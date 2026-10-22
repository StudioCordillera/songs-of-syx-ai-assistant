"""Copied-game own-panel -> file IPC -> candidate references -> durable plain reply.

Deterministic fake provider only; no key reading or external inference. The
unchanged ChatBackgroundScenario supplies fixed public test-only own-widget/speed
operations; this verifier never sends native input or game commands.
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
from syx_chat_store import ChatStore
from dev.blueprint_coordinator_candidate import BlueprintCoordinator
from dev.blueprint_examples import load_registry
from dev.blueprint_chat_candidate import EXTRA
from dev.blueprint_mcp_candidate import isolated_state_dir

SOURCES = ['dev/verify_blueprint_coordinator.py', 'dev/blueprint_coordinator_candidate.py',
    'dev/blueprint_chat_candidate.py', 'dev/blueprint_mcp_candidate.py', 'dev/blueprint_examples.py',
    'syx_chat_service.py', 'syx_chat.py', 'syx_chat_store.py', 'syx_mcp.py',
    'blueprint-examples-candidate.json', 'BLUEPRINT_CATALOG_VALIDATION.json']
ID = 'warehouse-two-items-teaching-grid'
CITATION = load_registry().citation()['artifacts'][0]['url']
ANSWER = ('SIMULATED FIXTURE ANSWER: original warehouse teaching grid, reviewed catalog 0.71.44. '
          'Construction, storage capacity, materials and efficiency are unverified. Source: ' + CITATION)


class ReferenceFixtureProvider:
    def __init__(self, directory):
        self.directory = directory
        self.calls = 0
        self.closed = False

    async def complete(self, messages, tools, emit):
        self.calls += 1
        assert len(tools) == 21 and EXTRA <= {t['function']['name'] for t in tools}
        if self.calls == 1:
            async with asyncio.timeout(75):
                while not (self.directory / 'release-simulated-answer').exists():
                    await asyncio.sleep(.05)
            name = 'search_blueprint_examples'
            request = {'query': 'warehouse aisle', 'game_version': '0.71.44'}
        elif self.calls == 2:
            result = json.loads(messages[-1]['content'])
            hit = json.loads(result['content'][0]['text'])['results'][0]
            assert hit['id'] == ID and 'geometry' not in hit
            name = 'get_blueprint_example'
            request = {'example_id': hit['id'], 'game_version': '0.71.44'}
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


async def verify(directory):
    directory = isolated_state_dir(str(directory))
    hashes = {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in SOURCES}
    store = ChatStore(directory / 'blueprint-fixture-history')
    params = StdioServerParameters(command=sys.executable, args=['-m', 'dev.blueprint_mcp_candidate'],
        cwd=str(ROOT), env={'SYX_STATE_DIR': str(directory)})
    try:
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as mcp:
                await mcp.initialize()
                provider = ReferenceFixtureProvider(directory)
                coordinator = BlueprintCoordinator(store, mcp, directory, 'fixture-not-a-credential',
                    provider_factory=lambda _: provider)
                server = asyncio.create_task(coordinator.serve())
                completed = False
                try:
                    async with asyncio.timeout(110):
                        while not (directory / 'background-native.json').exists():
                            if server.done():
                                await server
                                raise AssertionError('Coordinator exited early')
                            if coordinator.selected:
                                turns = store.turns(coordinator.selected)
                                assert not any(t['status'] in {'failed', 'cancelled'} for t in turns)
                                if turns and turns[0]['status'] == 'completed':
                                    completed = True
                                    (directory / 'simulated-reply-completed').write_text('completed\n')
                            await asyncio.sleep(.05)
                    assert completed and provider.calls == 3 and provider.closed
                    native = json.loads((directory / 'background-native.json').read_text())
                    assert native['passed'] and native['reopened_same_chat']
                    assert len(native['checks']) == 3 and all(c['passed'] for c in native['checks'])
                    assert all(c['game_seconds_advanced'] > 0 for c in native['checks'][:2])
                    events = store.events(coordinator.selected)
                    calls = [e['payload'] for e in events if e['kind'] == 'tool']
                    assert [c['name'] for c in calls] == ['game_status', 'search_blueprint_examples', 'get_blueprint_example']
                    item = json.loads(calls[-1]['result']['content'][0]['text'])
                    assert item['citation'] == load_registry().citation()
                    ui = (directory / 'chat-ui.txt').read_text()
                    visible = [base64.b64decode(line[5:]).decode() for line in ui.splitlines() if line.startswith('line=')]
                    assert any(ANSWER in text for text in visible)
                    assert not any('"geometry"' in text or '"tool_calls"' in text for text in visible)
                    assert len(store.turns(coordinator.selected)) == 1
                    assert hashes == {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in SOURCES}
                    report = {'passed': True, 'checks': native['checks'], 'reopened_same_chat': True,
                        'source_sha256': hashes, 'simulated_provider_round_trips': provider.calls,
                        'external_inference_calls': 0, 'inference_calls': 0,
                        'actual_reference_tool_calls': 2, 'completed_turns': 1,
                        'simple_player_policy_preserved': True, 'immutable_citation_in_durable_evidence': True,
                        'plain_reply_in_native_ipc_on_reopen': True, 'production_integrated': False,
                        'limits': ['One copied city, speed 1 and fixed public test-only own-widget operations; no physical/native input or screenshots.',
                            'Three fake-provider rounds explicitly request the original reference example. No real model/schema/advice/network acceptance is claimed.',
                            'Production Java panel/JAR is unchanged. Its IPC receives plain fixture text; no unobscured rendering/read receipt, badge, drag/resize/theme or target-chip acceptance.',
                            'Runtime identity is a load session, not a permanent world. No construction or gameplay command is provided.']}
                    (directory / 'blueprint-coordinator-validation.json').write_text(json.dumps(report, indent=2) + '\n')
                    (directory / 'verifier.done').write_text('passed\n')
                    return report
                finally:
                    server.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await server
    finally:
        store.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', type=Path, required=True)
    asyncio.run(verify(parser.parse_args().state_dir))
