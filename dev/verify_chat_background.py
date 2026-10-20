"""Real copied-game/UI/coordinator/MCP test with explicitly simulated inference latency.

No credentials or external inference. Does not validate real provider latency,
physical input, badges (not implemented), every view, or player save identity.
"""
import argparse
import asyncio
import base64
import json
import os
from pathlib import Path
import sys
import time

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from syx_chat_store import ChatStore
from syx_chat_service import Coordinator


class DelayedFixtureProvider:
    def __init__(self, directory):
        self.directory = directory
        self.calls = 0

    async def complete(self, messages, tools, on_text):
        self.calls += 1
        async with asyncio.timeout(75):
            while not (self.directory/'release-simulated-answer').exists():
                await asyncio.sleep(.1)
        text = 'SIMULATED FIXTURE ANSWER: completed while chat was closed.'
        on_text(text)
        return {'role': 'assistant', 'content': text}

    async def close(self):
        pass


async def verify(directory):
    directory = directory.resolve()
    root = Path(__file__).resolve().parent.parent
    store = ChatStore(directory/'fixture-history')
    params = StdioServerParameters(command=sys.executable, args=['-m', 'syx_mcp'], cwd=str(root),
        env={k: v for k, v in {**os.environ, 'SYX_STATE_DIR': str(directory)}.items()
             if k not in {'DEEPSEEK_API_KEY', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY'}})
    try:
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as mcp:
                await mcp.initialize()
                coordinator = Coordinator(store, mcp, directory, 'fixture-not-a-credential', simple=True)
                provider = DelayedFixtureProvider(directory)
                coordinator.loop.provider_factory = lambda _: provider
                server = asyncio.create_task(coordinator.serve())
                try:
                    deadline = time.monotonic()+95
                    completed = False
                    while time.monotonic()<deadline:
                        if server.done():
                            await server
                            raise AssertionError('Coordinator exited early')
                        if coordinator.selected:
                            cid = coordinator.selected
                            turns = store.turns(cid)
                            if turns and turns[0]['status'] in {'failed', 'cancelled'}:
                                raise AssertionError('Simulated turn failed; inspect private fixture history')
                            if turns and turns[0]['status'] == 'completed':
                                completed = True
                                (directory/'simulated-reply-completed').write_text('completed\n')
                        if (directory/'background-native.json').exists():
                            break
                        await asyncio.sleep(.1)
                    assert completed and provider.calls == 1
                    native = json.loads((directory/'background-native.json').read_text())
                    assert native['passed'] and native['reopened_same_chat']
                    assert len(native['checks']) == 3 and all(x['passed'] for x in native['checks'])
                    assert all(x['game_seconds_advanced'] > 0 for x in native['checks'][:2])
                    events = store.events(coordinator.selected)
                    final = [x for x in events if x['kind'] == 'assistant' and x['payload'].get('completed')]
                    assert len(final) == 1 and final[0]['payload']['text'].startswith('SIMULATED FIXTURE ANSWER:')
                    ui = (directory/'chat-ui.txt').read_text()
                    visible = [base64.b64decode(x[5:]).decode() for x in ui.splitlines() if x.startswith('line=')]
                    assert any('SIMULATED FIXTURE ANSWER:' in x for x in visible)
                    report = {'passed': True, 'checks': native['checks'], 'reopened_same_chat': True,
                        'real_game_time_progression': True, 'real_coordinator_mcp_history_path': True,
                        'simulated_provider_calls': provider.calls, 'external_inference_calls': 0,
                        'completed_turns': len(final), 'completed_reply_visible_on_reopen': True,
                        'unread_badge_implemented': False,
                        'limits': ['One copied city at speed 1; public test-only speed/own-widget actions, no native input or save writes.',
                            'Inference is deliberately simulated; actual network/provider failure/latency are not acceptance here.',
                            'No physical keyboard/pointer, every-view, world grouping, auto-attachment or unread-badge acceptance.']}
                    (directory/'chat-background-validation.json').write_text(json.dumps(report, indent=2)+'\n')
                    (directory/'verifier.done').write_text('verified\n')
                    print('PASS open/closed unpaused chat with simulated delayed inference', flush=True)
                finally:
                    server.cancel()
                    try:
                        await server
                    except asyncio.CancelledError:
                        pass
    finally:
        store.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state-dir', type=Path, required=True)
    asyncio.run(verify(p.parse_args().state_dir))
