"""Real file IPC and stdio reference workflow with synthetic snapshots/fake inference."""
import asyncio
import base64
import contextlib
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from uuid import uuid4

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from syx_chat_store import ChatStore
from syx_chat_service import Coordinator, b64
from syx_chat import TOOLS
from dev.blueprint_coordinator_candidate import BlueprintCoordinator
from dev.verify_blueprint_coordinator import ReferenceFixtureProvider, ANSWER

ROOT = Path(__file__).resolve().parent


def test_candidate_refuses_non_disposable_state_or_history_before_action_journal(tmp_path):
    store = ChatStore(tmp_path / 'private-history')
    try:
        with tempfile.TemporaryDirectory(dir=ROOT / 'runtime', prefix='blueprint-coordinator-') as name:
            for state in [tmp_path, Path(name)]:
                with pytest.raises(ValueError):
                    BlueprintCoordinator(store, None, state, '', provider_factory=lambda _: None)
        assert store.db.execute("SELECT name FROM sqlite_master WHERE name='actions'").fetchone() is None
    finally:
        store.close()


@pytest.mark.parametrize('mode', ['completed', 'stop', 'demo_refused'])
def test_real_ipc_reference_reply_duplicate_action_and_stop_keep_simple_policy(mode):
    asyncio.run(ipc_scenario(mode))


async def ipc_scenario(mode):
    with tempfile.TemporaryDirectory(dir=ROOT / 'runtime', prefix='blueprint-coordinator-ipc-') as name:
        directory = Path(name)
        snapshot = json.loads((ROOT / 'snapshot.example.json').read_text())
        session = str(uuid4())
        snapshot['session_id'] = session
        assert snapshot['demo'] is True
        # Authored positive admission control, not a native observation. Keep
        # DEMO-unverified version and synthetic domain qualifiers. The negative
        # control retains demo=True and must be refused by the unchanged guard.
        if mode != 'demo_refused': snapshot['demo'] = False
        async def heartbeat():
            while True:
                snapshot['captured_at'] = datetime.now(timezone.utc).isoformat()
                pending = directory / 'snapshot.pending'
                pending.write_text(json.dumps(snapshot))
                pending.replace(directory / 'snapshot.json')
                await asyncio.sleep(.1)
        clock = asyncio.create_task(heartbeat())
        await asyncio.sleep(0)
        store = ChatStore(directory / 'history')
        params = StdioServerParameters(command=sys.executable, args=['-m', 'dev.blueprint_mcp_candidate'],
            cwd=str(ROOT), env={'SYX_STATE_DIR': str(directory)})
        try:
            async with stdio_client(params) as streams:
                async with ClientSession(*streams) as mcp:
                    await mcp.initialize()
                    provider = ReferenceFixtureProvider(directory)
                    class CountedCoordinator(BlueprintCoordinator):
                        async def dispatch(self, request):
                            processed.append(request['request_id'])
                            return await super().dispatch(request)
                    processed = []
                    candidate = CountedCoordinator(store, mcp, directory, 'fixture-not-a-credential',
                        provider_factory=lambda _: provider)
                    baseline = Coordinator(store, mcp, directory, '', simple=True)
                    assert baseline.loop.instructions in candidate.loop.instructions
                    assert len(TOOLS) == 19 and candidate.simple is True
                    server = asyncio.create_task(candidate.serve())
                    async def wait_for(condition):
                        async with asyncio.timeout(10):
                            while not condition():
                                if server.done():
                                    await server
                                    raise AssertionError('Coordinator exited')
                                await asyncio.sleep(.01)
                    async def send(action, *, request_id=None, chat_id=None, text=None):
                        rid = request_id or str(uuid4())
                        lines = ['protocol=2', 'request_id=' + rid, 'action=' + action, 'session_id=' + session]
                        if chat_id: lines.append('chat_id=' + chat_id)
                        if text is not None: lines.append('text=' + b64(text))
                        raw = '\n'.join(lines) + '\n'
                        pending = directory / 'action.pending'
                        pending.write_text(raw)
                        pending.replace(directory / 'chat-action.txt')
                        await wait_for(lambda: candidate.ack == rid)
                        return rid
                    try:
                        await send('sync')
                        if mode == 'demo_refused':
                            await wait_for(lambda: candidate.notice.startswith('Waiting for a fresh matching'))
                            assert candidate.selected is None and provider.calls == 0
                            assert store.list() == []
                            return
                        await wait_for(lambda: candidate.selected is not None)
                        cid = candidate.selected
                        assert store.chat(cid)['model'] == 'deepseek-v4-pro'
                        rid = await send('send', chat_id=cid, text='Show the original warehouse teaching example')
                        await wait_for(lambda: provider.calls == 1)
                        assert not candidate.tasks[cid].done()
                        # Different valid field order forces parsing and durable duplicate
                        # admission again; an invalid blank line would test only parse refusal.
                        action_path = directory / 'chat-action.txt'
                        pending = directory / 'action.pending'
                        pending.write_text('\n'.join(reversed(action_path.read_text().splitlines())) + '\n')
                        pending.replace(action_path)
                        await wait_for(lambda: processed.count(rid) == 2)
                        assert len(store.turns(cid)) == 1 and provider.calls == 1
                        if mode == 'stop':
                            await send('stop', chat_id=cid)
                        else:
                            (directory / 'release-simulated-answer').write_text('release\n')
                        await wait_for(lambda: candidate.tasks[cid].done())
                        assert provider.closed
                        assert store.turns(cid)[0]['status'] == ('cancelled' if mode == 'stop' else 'completed')
                        assert provider.calls == (1 if mode == 'stop' else 3)
                        if mode != 'stop':
                            await wait_for(lambda: ANSWER in '\n'.join(base64.b64decode(line[5:]).decode()
                                for line in (directory / 'chat-ui.txt').read_text().splitlines() if line.startswith('line=')))
                            visible = [base64.b64decode(line[5:]).decode() for line in
                                (directory / 'chat-ui.txt').read_text().splitlines() if line.startswith('line=')]
                            assert not any('"geometry"' in s or '"tool_calls"' in s for s in visible)
                            tool_events = [e for e in store.events(cid) if e['kind'] == 'tool']
                            assert [e['payload']['name'] for e in tool_events] == ['game_status', 'search_blueprint_examples', 'get_blueprint_example']
                        assert candidate.expanded == set()
                    finally:
                        server.cancel()
                        with contextlib.suppress(asyncio.CancelledError): await server
        finally:
            clock.cancel()
            with contextlib.suppress(asyncio.CancelledError): await clock
            store.close()
