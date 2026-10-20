"""Actual mod/coordinator/MCP reload handshake with two explicitly simulated replies."""
import argparse
import asyncio
import base64
import json
import os
from pathlib import Path
import sys
import time
from uuid import uuid4

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from syx_chat_service import Coordinator
from syx_chat_store import ChatStore
from syx_mcp import Advisor


async def verify(directory):
    directory = directory.resolve()
    root = Path(__file__).resolve().parent.parent
    advisor = Advisor(directory/'snapshot.json', directory/'corpus.json')
    store = ChatStore(directory/'fixture-history')
    providers = []
    class FixtureProvider:
        def __init__(self):self.messages = None
        async def complete(self, messages, tools, emit):
            self.messages = list(messages)
            text = 'Simulated fixture answer '+str(len(providers))
            emit(text)
            return {'role':'assistant', 'content':text}
        async def close(self):pass
    def factory(_):
        p = FixtureProvider()
        providers.append(p)
        assert len(providers) <= 2, 'Unexpected third simulated inference'
        return p
    params = StdioServerParameters(command=sys.executable, args=['-m', 'syx_mcp'], cwd=str(root),
        env={k:v for k,v in {**os.environ, 'SYX_STATE_DIR':str(directory)}.items()
             if k not in {'DEEPSEEK_API_KEY','ANTHROPIC_API_KEY','OPENAI_API_KEY'}})
    try:
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as mcp:
                await mcp.initialize()
                coordinator = Coordinator(store, mcp, directory, 'fixture-not-a-credential', simple=True)
                coordinator.loop.provider_factory = factory
                write_ui = coordinator.write_ui
                def ui():
                    write_ui()
                    if (directory/'test-old-protocol').exists() and not (directory/'protocol-refusal-checked').exists():
                        p = directory/'chat-ui.txt'
                        temporary = directory/'fixture-v1.tmp'
                        temporary.write_text(p.read_text().replace('protocol=2\n', 'protocol=1\n', 1))
                        os.replace(temporary, p)
                coordinator.write_ui = ui
                server = asyncio.create_task(coordinator.serve())
                first_session = None
                extra_chat = None
                original_chat = None
                switched = switched_back = error_injected = False
                first_events = None
                deadline = time.monotonic()+215
                try:
                    while time.monotonic()<deadline:
                        if server.done():await server;raise AssertionError('Coordinator exited early')
                        try:
                            phase = json.loads((directory/'native-phase.json').read_text())
                            status = advisor.status()
                            if status.get('live') is True and status.get('session_id') == phase['session_id']:
                                (directory/('session-ready-'+phase['session_id'])).touch()
                            if phase['phase']=='initial':first_session = phase['session_id']
                        except (FileNotFoundError, json.JSONDecodeError):pass
                        if coordinator.selected and first_events is None:
                            turns = store.turns(coordinator.selected)
                            if turns and turns[0]['status']=='completed':
                                first_events = store.events(coordinator.selected)
                        if (directory/'test-reconnect-notice').exists() and not error_injected:
                            coordinator.notice='Game connection timed out; no question was sent'
                            error_injected=True
                        if (directory/'populate-filters').exists() and not (directory/'filters-populated.done').exists():
                            assert first_session
                            original_chat = coordinator.selected
                            extra_chat = store.new(first_session, 'Earlier load fixture', model='deepseek-v4-pro')['chat_id']
                            ui()
                            (directory/'filters-populated.done').touch()
                        if (directory/'draft-switch-request').exists() and not switched:
                            await coordinator.dispatch(dict(request_id=str(uuid4()), action='select',
                                session_id=store.chat(original_chat)['attached_session'], chat_id=extra_chat))
                            switched = True
                        if (directory/'draft-switch-back').exists() and not switched_back:
                            await coordinator.dispatch(dict(request_id=str(uuid4()), action='select',
                                session_id=store.chat(original_chat)['attached_session'], chat_id=original_chat))
                            switched_back = True
                        if (directory/'auto-native-validation.json').exists():break
                        await asyncio.sleep(.1)
                    native = json.loads((directory/'auto-native-validation.json').read_text())
                    assert native['passed'] and len(native['checks'])==7 and native['reloads']==1 and switched_back
                    assert len(providers)==2 and first_events is not None
                    cid = coordinator.selected
                    turns = store.turns(cid)
                    assert len(turns)==2 and all(t['status']=='completed' for t in turns)
                    assert turns[0]['game_session'] != turns[1]['game_session']
                    assert store.events(cid)[:len(first_events)] == first_events
                    boundaries = [e for e in store.events(cid) if e['kind']=='session_boundary']
                    assert len(boundaries)==1 and boundaries[0]['payload']['automatic_current_game'] is True
                    assert boundaries[0]['payload']['explicit_continuation'] is False
                    assert not any(m['role']=='assistant' for m in providers[1].messages)
                    assert 'Simulated fixture answer 1' in providers[1].messages[1]['content']
                    before = store.chat(cid)
                    try:
                        await coordinator.dispatch(dict(protocol='2', request_id=str(uuid4()), action='send',
                            session_id=str(uuid4()), chat_id=cid, text='Forged mismatched runtime fixture'))
                    except ValueError as e:assert 'fresh matching' in str(e)
                    else:raise AssertionError('Wrong-session send was accepted')
                    assert store.chat(cid)==before and len(store.turns(cid))==2 and len(providers)==2
                    ui()
                    visible = [base64.b64decode(x[5:]).decode() for x in (directory/'chat-ui.txt').read_text().splitlines() if x.startswith('line=')]
                    assert 'Earlier game · Assistant: Simulated fixture answer 1' in visible
                    report = {'passed':True,'native_checks':native['checks'],'real_reload':True,
                        'automatic_first_chat':True,'automatic_reconnect_on_question':True,
                        'historical_events_unchanged':True,'historical_transcript_labeled':True,
                        'provider_context_reset_after_reload':True,'wrong_session_rejected_without_turn':True,
                        'protocol_1_refused_and_protocol_2_recovered_with_draft':True,
                        'unsent_draft_survives_chat_selection_round_trip':True,
                        'older_chat_error_notice_not_hidden_by_reconnect_hint':True,
                        'completed_turns':2,'simulated_provider_calls':2,'external_inference_calls':0,
                        'limits':['Copied city and one reload; own public widget controls, no physical keyboard/pointer or every scene.',
                            'Two fake provider answers through real coordinator/MCP/history, not paid/authenticated provider acceptance.',
                            'Current-load filter is runtime attachment, not permanent world grouping. No unread badge or managed helper startup.',
                            'Protocol refusal changes the version line of this fixture helper; not exhaustive mixed-version compatibility.']}
                    (directory/'auto-connection-validation.json').write_text(json.dumps(report, indent=2)+'\n')
                    (directory/'verifier.done').touch()
                    print('Automatic connection, reload, filters and protocol refusal passed', flush=True)
                finally:
                    server.cancel()
                    try:await server
                    except asyncio.CancelledError:pass
    finally:store.close()


async def verify_focus(directory):
    directory=directory.resolve();root=Path(__file__).resolve().parent.parent
    store=ChatStore(directory/'fixture-history')
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(root),
        env={k:v for k,v in {**os.environ,'SYX_STATE_DIR':str(directory)}.items()
             if k not in {'DEEPSEEK_API_KEY','ANTHROPIC_API_KEY','OPENAI_API_KEY'}})
    try:
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as mcp:
                await mcp.initialize()
                coordinator=Coordinator(store,mcp,directory,'',simple=True)
                def refuse(_):raise AssertionError('Missing-key focus fixture must not create a provider')
                coordinator.loop.provider_factory=refuse
                task=asyncio.create_task(coordinator.serve())
                try:
                    deadline=time.monotonic()+100
                    while not (directory/'chat-gui-validation.json').exists() and time.monotonic()<deadline:
                        if task.done():await task;raise AssertionError('Coordinator exited early')
                        await asyncio.sleep(.1)
                    report=json.loads((directory/'chat-gui-validation.json').read_text());assert report['passed']
                    assert len(store.list())==1 and store.turns(coordinator.selected)==[] and not coordinator.tasks
                    report.update(inference_calls=0,no_provider_turns_created=True)
                    (directory/'auto-connection-validation.json').write_text(json.dumps(report,indent=2)+'\n')
                    (directory/'verifier.done').touch()
                    print('Current panel focus, wrapping, missing-key and view persistence passed',flush=True)
                finally:
                    task.cancel()
                    try:await task
                    except asyncio.CancelledError:pass
    finally:store.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state-dir',type=Path,required=True)
    p.add_argument('--case',choices=['connection','focus'],default='connection')
    args=p.parse_args()
    asyncio.run((verify_focus if args.case=='focus' else verify)(args.state_dir))
