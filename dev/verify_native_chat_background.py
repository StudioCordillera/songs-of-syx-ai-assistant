"""Own native layout plus production coordinator/MCP/history; fake inference only.

No credential read, paid network request, OS input or normal game/profile access.
"""
import argparse
import asyncio
import base64
import contextlib
import hashlib
import json
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from syx_chat_service import Coordinator, action
from syx_chat_store import ChatStore
from syx_blueprint_chat import BlueprintConversation, EXTRA
from syx_blueprints import load_registry
from dev.blueprint_mcp_candidate import isolated_state_dir

ID = 'warehouse-two-items-teaching-grid'
CITATION = load_registry().citation()['artifacts'][0]['url']
ANSWER = ('SIMULATED FIXTURE ANSWER: original warehouse teaching grid, reviewed catalog 0.71.44. '
          'Construction, storage capacity, materials and efficiency are unverified. Source: ' + CITATION)
CHECKS = {'automatic_native_session', 'responsive_pending_draft_partial', 'open_pending',
          'closed_pending', 'closed_completed', 'reopened_same_chat_reply', 'stop_second_turn'}
SOURCES = ['dev/verify_native_chat_background.py', 'syx_chat_service.py', 'syx_chat.py',
    'syx_chat_store.py', 'syx_mcp.py', 'syx_blueprint_chat.py', 'syx_blueprint_tools.py',
    'syx_blueprints.py', 'syx_blueprint_data.py', 'dev/blueprint_mcp_candidate.py', 'dev/verify_native_chat_recovery.py', 'dev/verify_native_chat_notices.py', 'dev/chat_recovery_candidate.py']


class FixtureProvider:
    def __init__(self, directory, number):
        self.directory, self.number = directory, number
        self.calls, self.closed = 0, False

    async def gate(self, name):
        async with asyncio.timeout(85):
            while not (self.directory / name).exists():
                await asyncio.sleep(.05)

    async def complete(self, messages, tools, emit):
        self.calls += 1
        assert len(tools) == 21 and EXTRA <= {t['function']['name'] for t in tools}
        if self.number == 2:
            assert self.calls == 1
            (self.directory / 'second-provider-started').write_text('started\n')
            await asyncio.Future()  # Cancelled only by the normal coordinator Stop.
        assert self.number == 1
        if self.calls == 1:
            await self.gate('release-layout-partial')
            emit('SIMULATED partial; deterministic fixture, no external inference.')
            await self.gate('release-simulated-answer')
            name, request = 'search_blueprint_examples', {'query': 'warehouse aisle', 'game_version': '0.71.44'}
        elif self.calls == 2:
            result = json.loads(messages[-1]['content'])
            hit = json.loads(result['content'][0]['text'])['results'][0]
            assert hit['id'] == ID and 'geometry' not in hit
            name, request = 'get_blueprint_example', {'example_id': ID, 'game_version': '0.71.44'}
        else:
            assert self.calls == 3
            result = json.loads(messages[-1]['content'])
            item = json.loads(result['content'][0]['text'])
            assert item['geometry']['grid'] == ['.....', '.RF..', 'E....', '.RF..', '.....']
            assert item['citation'] == load_registry().citation()
            assert item['execution_supported'] is item['construction_validated'] is False
            emit(ANSWER)
            return {'role': 'assistant', 'content': ANSWER}
        return {'role': 'assistant', 'content': '', 'tool_calls': [{
            'id': str(uuid4()), 'type': 'function',
            'function': {'name': name, 'arguments': json.dumps({'request': request})}}]}

    async def close(self):
        self.closed = True
        if self.number == 2:
            (self.directory / 'second-provider-closed').write_text('closed\n')


async def verify(directory, *, recovery=False, notices=False):
    if notices and not recovery:
        raise ValueError("Notice fixture requires the recovery lifecycle")
    directory = isolated_state_dir(str(directory))
    hashes = {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in SOURCES}
    store = ChatStore(directory / 'layout-fixture-history')
    providers = []
    def factory(chat):
        assert chat['model'] == 'deepseek-v4-pro' and len(providers) < 2, 'No inference may be replayed after restart'
        provider = FixtureProvider(directory, len(providers) + 1)
        providers.append(provider)
        return provider
    params = StdioServerParameters(command=sys.executable, args=['-m', 'syx_mcp'],
        cwd=str(ROOT), env={'SYX_STATE_DIR': str(directory)})
    try:
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as mcp:
                await mcp.initialize()
                def new_coordinator():
                    if notices:
                        from dev.chat_recovery_candidate import RecoveryCoordinator
                        result = RecoveryCoordinator(store, mcp, directory, 'fixture-not-a-credential')
                    else:
                        result = Coordinator(store, mcp, directory, 'fixture-not-a-credential', simple=True)
                    original = result.loop
                    result.loop = BlueprintConversation(store, mcp, factory)
                    result.loop.instructions = original.instructions
                    return result
                coordinator = new_coordinator()
                server = asyncio.create_task(coordinator.serve())
                restarted = replayed = False
                notice_reopened = unknown_checked = False
                original_chat = None
                try:
                    async with asyncio.timeout(150):
                        while not (directory / 'layout-background-native.json').exists():
                            if server.done():
                                await server
                                raise AssertionError('Coordinator exited early')
                            if coordinator.selected:
                                turns = store.turns(coordinator.selected)
                                assert not any(t['status'] == 'failed' for t in turns)
                                if turns and turns[0]['status'] == 'completed':
                                    (directory / 'simulated-reply-completed').write_text('completed\n')
                            if recovery and not restarted and (directory / 'restart-helper-request').exists():
                                original_chat = coordinator.selected
                                assert [t['status'] for t in store.turns(original_chat)] == ['completed', 'cancelled']
                                assert all(p.closed for p in providers)
                                server.cancel()
                                with contextlib.suppress(asyncio.CancelledError):
                                    await server
                                store.close()
                                store = ChatStore(directory / 'layout-fixture-history')
                                coordinator = new_coordinator()
                                server = asyncio.create_task(coordinator.serve())
                                restarted = True
                            if restarted and coordinator.selected == original_chat:
                                (directory / 'helper-restarted').write_text('selected through real native auto-sync\n')
                            if restarted and not replayed and (directory / 'native-recovery-acknowledged').exists():
                                before = store.turns(original_chat)
                                user = next(e for e in store.events(original_chat) if e['kind'] == 'user')
                                replay = ('protocol=2\nrequest_id=' + before[0]['turn_id'] + '\naction=send\nsession_id=' + before[0]['game_session'] +
                                          '\nchat_id=' + original_chat + '\ntext=' + base64.b64encode(user['payload']['text'].encode()).decode() + '\n')
                                await coordinator.dispatch(action(replay.encode('ascii')))
                                assert store.turns(original_chat) == before and not coordinator.tasks
                                assert len(providers) == 2
                                replayed = True
                                (directory / 'duplicate-admission-checked').write_text('deduplicated\n')
                            if notices and replayed and not notice_reopened and (directory / 'notice-fixture-request').exists():
                                assert not coordinator.tasks or all(t.done() for t in coordinator.tasks.values())
                                # Authored local-history setup, not an inference request or a process crash.
                                store.begin(original_chat, str(uuid4()), store.chat(original_chat)['attached_session'],
                                    'AUTHORED fixture running turn; no inference was requested')
                                server.cancel()
                                with contextlib.suppress(asyncio.CancelledError):
                                    await server
                                store.close()
                                store = ChatStore(directory / 'layout-fixture-history', recover=True)
                                coordinator = new_coordinator()
                                server = asyncio.create_task(coordinator.serve())
                                notice_reopened = True
                            if notice_reopened and coordinator.selected == original_chat:
                                from dev.chat_recovery_candidate import INTERRUPTED, UNKNOWN
                                if not unknown_checked:
                                    assert coordinator.recovery_notice() == INTERRUPTED
                                    (directory / 'interrupted-notice-ready').write_text('authored stored status, new helper frame required\n')
                                if not unknown_checked and (directory / 'native-interrupted-notice-acknowledged').exists():
                                    gap = ('protocol=2\nrequest_id=' + str(uuid4()) + '\naction=send\nsession_id=' +
                                        store.chat(original_chat)['attached_session'] + '\nchat_id=' + original_chat +
                                        '\ntext=' + base64.b64encode(b'AUTHORED admission-gap fixture').decode() + '\n')
                                    request = action(gap.encode('ascii'))
                                    original_current_game = coordinator.current_game
                                    async def refused_admission(session):
                                        raise ValueError('Authored fixture admission interruption')
                                    coordinator.current_game = refused_admission
                                    before = store.turns(original_chat), store.events(original_chat)
                                    try:
                                        try:
                                            await coordinator.dispatch(request)
                                        except ValueError as error:
                                            assert str(error) == 'Authored fixture admission interruption'
                                        else:
                                            raise AssertionError('Fixed admission gap was not exercised')
                                    finally:
                                        coordinator.current_game = original_current_game
                                    await coordinator.dispatch(request)
                                    assert (store.turns(original_chat), store.events(original_chat)) == before
                                    assert len(providers) == 2 and not coordinator.tasks
                                    assert coordinator.recovery_notice() == UNKNOWN
                                    coordinator.notice = 'Authored admission-gap fixture. No new inference.'
                                    unknown_checked = True
                                    (directory / 'unknown-notice-ready').write_text('authored duplicate with no turn\n')
                            await asyncio.sleep(.05)
                    assert len(providers) == 2 and [p.calls for p in providers] == [3, 1]
                    assert all(p.closed for p in providers)
                    native = json.loads((directory / 'layout-background-native.json').read_text())
                    assert native['passed'] and native['reopened_same_chat']
                    expected = CHECKS | ({'helper_restart_restores_chat_draft', 'replayed_send_does_not_start_reply'} if recovery else set())
                    if notices:
                        expected |= {'native_interrupted_notice_preserves_draft', 'native_unknown_send_notice_no_inference'}
                        assert notice_reopened and unknown_checked
                    assert {x['phase'] for x in native['checks']} == expected and len(native['checks']) == len(expected)
                    assert not recovery or (restarted and replayed)
                    assert all(x['passed'] for x in native['checks'])
                    assert all(x['game_seconds_advanced'] > 0 for x in native['checks'] if x['phase'] in {'open_pending', 'closed_pending'})
                    assert [t['status'] for t in store.turns(coordinator.selected)] == (['completed', 'cancelled', 'interrupted'] if notices else ['completed', 'cancelled'])
                    events = store.events(coordinator.selected)
                    final = [e for e in events if e['kind'] == 'assistant' and e['payload'].get('completed')]
                    assert len(final) == 1 and final[0]['payload']['text'] == ANSWER
                    calls = [e['payload'] for e in events if e['kind'] == 'tool']
                    names = [c['name'] for c in calls]
                    assert names == ['game_status', 'search_blueprint_examples', 'get_blueprint_example', 'game_status']
                    item = json.loads(calls[2]['result']['content'][0]['text'])
                    assert item['citation'] == load_registry().citation()
                    rows = [base64.b64decode(r[5:]).decode() for r in (directory / 'chat-ui.txt').read_text().splitlines() if r.startswith('line=')]
                    assert any(ANSWER in row for row in rows)
                    assert not any('"geometry"' in row or '"tool_calls"' in row for row in rows)
                    assert hashes == {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in SOURCES}
                    report = {'passed': True, 'native_checks': native, 'source_sha256': hashes,
                        'real_production_coordinator_mcp_history': True, 'fake_provider_factory_injected': True,
                        'simulated_provider_round_trips': 4, 'external_inference_calls': 0,
                        'completed_turns': 1, 'cancelled_turns': 1, 'actual_reference_tool_calls': 2,
                        'plain_completed_reply_in_native_panel_model': True, 'production_integrated': False,
                        'coordinator_and_sqlite_reopened': restarted, 'original_send_deduplicated_after_restart': replayed,
                        'helper_process_restarted': False, 'mcp_transport_restarted': False,
                        'developer_recovery_notice_coordinator': notices, 'authored_running_turn_recovered': notice_reopened,
                        'authored_admission_gap_replayed_without_inference': unknown_checked,
                        'limits': ['Developer own-class overlay only, not a changed released JAR. One copied city at speed 1.',
                            'Supplied own launcher/resize gesture primitives and public own Send/Close/Stop routing; no OS input, engine pointer/button mutation or screenshots.',
                            'Real default production coordinator, stdio MCP and disposable SQLite history with a deterministic injected fake provider; no real model, paid network or advice-quality acceptance.',
                            'Panel transcript/model and own-handle render callbacks do not prove unobscured display, physical focus, human reading or receipts. No badge, production preference path or typed chips; this-run palette controls do not establish native pixel contrast.',
                            'Public test-only speed/view operations and engine autosaves stay in the disposable profile; no explicit game save requested. Permanent world identity and gameplay execution are absent.']}
                    if recovery:
                        report['limits'].append('Graceful coordinator-task stop and a new Coordinator/SQLite connection in the same verifier process; native game and stdio MCP stay running. No abrupt crash, pending-turn recovery, helper-process/network restart, billing or native display/read proof.')
                    if notices:
                        report['limits'].append('Two native notice phases use explicitly authored disposable running-turn/admission-gap setup. Recovery is a graceful task/SQLite reopen, not an actual crash or pending paid call. Candidate notice rows/model checks do not prove human readability or unobscured display.')
                    (directory / ('native-chat-notices-validation.json' if notices else 'native-chat-recovery-validation.json' if recovery else 'native-chat-background-validation.json')).write_text(json.dumps(report, indent=2) + '\n')
                    (directory / 'verifier.done').write_text('passed\n')
                finally:
                    server.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await server
    finally:
        store.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state-dir', type=Path, required=True)
    asyncio.run(verify(p.parse_args().state_dir))
