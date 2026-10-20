"""Actual stdio MCP transport; production tool server, synthetic game readers."""
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult, TextContent
import pytest

from dev.chat_target_transport import McpTargetDrafts

ROOT = Path(__file__).resolve().parent


@pytest.fixture
def transport_state(tmp_path):
    state = json.loads((ROOT / 'snapshot.example.json').read_text())
    state.update(demo=False, game_loaded=True, game_version='0.71.44', session_id=str(uuid4()),
                 scene={'active_view': 'settlement'}, captured_at=datetime.now(timezone.utc).isoformat())
    path = tmp_path / 'snapshot.json'
    path.write_text(json.dumps(state))
    return path, state


def parameters(path):
    env = {k: v for k, v in os.environ.items() if not any(x in k.upper() for x in ('API_KEY', 'TOKEN'))}
    return StdioServerParameters(command=sys.executable, args=[str(ROOT / 'dev/target_transport_fixture.py'),
                                 '--snapshot', str(path)], env=env, cwd=str(ROOT))


async def create(session, kind='entity'):
    name, spec = {
        'entity': ('capture_live_entities', {}),
        'tile': ('capture_live_tiles', {'tile_bounds': [0, 0, 3, 1]}),
        'regional_output': ('capture_live_regional_outputs', {'region_ids': [0, 1, 2], 'resource_ids': ['grain']}),
    }[kind]
    result = await session.call_tool(name, {'spec': spec})
    assert not result.is_error
    value = result.structured_content or json.loads(result.content[0].text)
    return value['capture']['capture_id']


def test_stdio_three_kinds_revalidated_without_recapture_and_isolated_drafts(transport_state):
    path, _ = transport_state
    async def run():
        async with stdio_client(parameters(path)) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                tokens = {k: await create(session, k) for k in ('entity', 'tile', 'regional_output')}
                adapter = McpTargetDrafts(session)
                real = session.call_tool;calls = []
                async def traced(name, arguments=None, **kw):
                    calls.append(name)
                    return await real(name, arguments, **kw)
                session.call_tool = traced
                chat = str(uuid4())
                for kind, token in tokens.items(): await adapter.stage(chat, kind, token, limit=2)
                envelope = await adapter.prepare(chat)
                assert len(envelope['attachments']) == 3 and envelope['has_attachments'] is True
                assert [a['capture']['scope'] for a in envelope['attachments']] == ['synthetic_transport_fixture'] * 3
                assert all(a['next_offset'] == 2 for a in envelope['attachments'])
                assert envelope['attachments'][1]['rows'][0]['room'] == {'available': False, 'data': None, 'reason': 'synthetic_unknown'}
                assert set(calls) == {'game_status', 'read_entity_capture', 'read_tile_capture', 'read_regional_output_capture'}
                assert calls.count('read_entity_capture') == 2  # stage + prepare, no new game capture
                assert adapter.preview(str(uuid4())) == []
                item = envelope['attachments'][0]
                item['rows'][0]['id'] = 999
                assert adapter.preview(chat)[0]['rows'][0]['id'] == 0
                await adapter.remove(chat, item['attachment_id'])
                assert len(adapter.preview(chat)) == 2
    asyncio.run(run())


def test_stdio_eviction_changed_runtime_and_independent_servers_refuse(transport_state):
    path, state = transport_state
    async def run():
        async with stdio_client(parameters(path)) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize();token = await create(session)
                adapter = McpTargetDrafts(session);chat = str(uuid4())
                item = await adapter.stage(chat, 'entity', token)
                async with stdio_client(parameters(path)) as other_streams:
                    async with ClientSession(*other_streams) as other:
                        await other.initialize()
                        with pytest.raises(ValueError, match='unavailable'):
                            await McpTargetDrafts(other).stage(chat, 'entity', token)
                for _ in range(3): await create(session)
                with pytest.raises(ValueError, match='unavailable'):
                    await adapter.prepare(chat)
                assert adapter.preview(chat) == [item]
                await adapter.remove(chat, item['attachment_id'])
                token = await create(session);item = await adapter.stage(chat, 'entity', token)
                state['session_id'] = str(uuid4());path.write_text(json.dumps(state))
                with pytest.raises(ValueError, match='runtime/version'):
                    await adapter.prepare(chat)
                assert adapter.preview(chat) == [item]
    asyncio.run(run())


def test_async_cancellation_timeout_and_new_chip_survive(transport_state, monkeypatch):
    path, _ = transport_state
    async def run():
        async with stdio_client(parameters(path)) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize();token = await create(session)
                adapter = McpTargetDrafts(session);chat = str(uuid4())
                first = await adapter.stage(chat, 'entity', token)
                real = adapter._call;entered = asyncio.Event()
                async def blocked(*args):
                    entered.set();await asyncio.Event().wait()
                adapter._call = blocked
                task = asyncio.create_task(adapter.prepare(chat));await entered.wait();task.cancel()
                with pytest.raises(asyncio.CancelledError): await task
                assert adapter.preview(chat) == [first]
                monkeypatch.setattr('dev.chat_target_transport.OPERATION_SECONDS', 0.03)
                with pytest.raises(ValueError, match='timed out'):
                    await adapter.prepare(chat)
                assert adapter.preview(chat) == [first]
                adapter._call = real
                monkeypatch.setattr('dev.chat_target_transport.OPERATION_SECONDS', 5)
                await adapter.stage(chat, 'entity', token, offset=1)
                assert len((await adapter.prepare(chat))['attachments']) == 2
    asyncio.run(run())


@pytest.mark.parametrize('mode', ['wrong_token', 'offset', 'kind', 'stale', 'bad_json', 'too_large', 'wrong_shape', 'boolean_cursor', 'missing_tick', 'timestamp', 'selection', 'over_cap', 'large_extra_text', 'multiple_blocks', 'missing_rows', 'deep_text', 'conflict'])
def test_malformed_remote_response_never_mutates_draft(transport_state, mode):
    path, _ = transport_state
    async def run():
        async with stdio_client(parameters(path)) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize();token = await create(session, 'tile')
                adapter = McpTargetDrafts(session);chat = str(uuid4());real = session.call_tool
                async def tampered(name, arguments=None, **kw):
                    result = await real(name, arguments, **kw)
                    if name == 'read_tile_capture':
                        value = result.structured_content or json.loads(result.content[0].text)
                        if mode == 'wrong_token': value['capture']['capture_id'] = str(uuid4())
                        elif mode == 'offset': value['offset'] = 9
                        elif mode == 'kind': value['capture']['capture_kind'] = 'entity'
                        elif mode == 'stale': value['current_state']['fresh'] = False
                        elif mode == 'bad_json': return CallToolResult(content=[TextContent(type='text', text='broken')])
                        elif mode == 'too_large': value['extra'] = 'é' * 65536
                        elif mode == 'wrong_shape': value['capture']['scene'] = None
                        elif mode == 'boolean_cursor': value['next_offset'] = True
                        elif mode == 'missing_tick': del value['capture']['tick']
                        elif mode == 'timestamp': value['capture']['captured_at'] = '2026-10-20T09:00:00'
                        elif mode == 'selection': value['capture']['selection'] = 'not-a-selection'
                        elif mode == 'over_cap': value['capture']['row_count'] = 101
                        elif mode == 'large_extra_text': return CallToolResult(content=[TextContent(type='text', text='é'*65536)], structuredContent=value)
                        elif mode == 'multiple_blocks': return CallToolResult(content=[TextContent(type='text',text='{}')]*2, structuredContent=value)
                        elif mode == 'missing_rows': value['rows'] = []
                        elif mode == 'deep_text': return CallToolResult(content=[TextContent(type='text', text='['*2000+'0'+']'*2000)])
                        elif mode == 'conflict': return CallToolResult(content=[TextContent(type='text', text='{}')], structuredContent=value)
                        return CallToolResult(content=[], structuredContent=value)
                    return result
                session.call_tool = tampered
                with pytest.raises(ValueError): await adapter.stage(chat, 'tile', token)
                assert adapter.preview(chat) == []
    asyncio.run(run())


def test_disconnected_session_preserves_preview_and_does_not_reconnect(transport_state, monkeypatch):
    path, _ = transport_state
    async def run():
        async with stdio_client(parameters(path)) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize();token = await create(session)
                adapter = McpTargetDrafts(session);chat = str(uuid4())
                item = await adapter.stage(chat, 'entity', token)
        monkeypatch.setattr('dev.chat_target_transport.OPERATION_SECONDS', 0.1)
        with pytest.raises(ValueError, match='unavailable|timed out'):
            await adapter.prepare(chat)
        assert adapter.preview(chat) == [item]
        await adapter.remove(chat, item['attachment_id'])
        assert adapter.preview(chat) == []
    asyncio.run(run())


def test_missing_readonly_contract_rejects_before_page_calls(transport_state):
    path, _ = transport_state
    async def run():
        async with stdio_client(parameters(path)) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize();token = await create(session)
                real = session.list_tools
                async def incomplete(*a, **kw):
                    result = await real(*a, **kw)
                    next(t for t in result.tools if t.name == 'read_entity_capture').annotations.read_only_hint = False
                    return result
                session.list_tools = incomplete
                adapter = McpTargetDrafts(session);chat = str(uuid4())
                with pytest.raises(ValueError, match='read-only'):
                    await adapter.stage(chat, 'entity', token)
                assert adapter.preview(chat) == []
    asyncio.run(run())


def test_remove_lock_timeout_retains_attachment(transport_state, monkeypatch):
    path, _ = transport_state
    async def run():
        async with stdio_client(parameters(path)) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize();token = await create(session)
                adapter = McpTargetDrafts(session);chat = str(uuid4())
                item = await adapter.stage(chat, 'entity', token)
                monkeypatch.setattr('dev.chat_target_transport.OPERATION_SECONDS', 0.03)
                async with adapter._lock:
                    with pytest.raises(ValueError, match='removal timed out'):
                        await adapter.remove(chat, item['attachment_id'])
                assert adapter.preview(chat) == [item]
    asyncio.run(run())
