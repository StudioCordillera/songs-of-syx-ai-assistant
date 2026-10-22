"""Bounded disposable helper-process crash checks; synthetic MCP and inference only."""
import argparse
import asyncio
import base64
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from mcp.types import CallToolResult, Tool, ToolAnnotations
from syx_blueprint_chat import BlueprintConversation, EXTRA
from syx_chat import TOOLS
from syx_chat_service import Coordinator, action
from syx_chat_store import ChatStore

STAGES = ('admitted_before_turn', 'streaming_partial', 'completed_before_ui')
SOURCES = ('dev/check_chat_process_recovery.py', 'syx_chat_service.py', 'syx_chat_store.py',
           'syx_chat.py', 'syx_blueprint_chat.py', 'dev/chat_recovery_candidate.py')
PARTIAL = 'SIMULATED volatile partial'
FINAL = 'SIMULATED completed answer'
QUESTION = 'Synthetic original question'


class SyntheticMCP:
    def __init__(self, session):
        self.session = session

    async def list_tools(self):
        return SimpleNamespace(tools=[Tool(name=n, input_schema={'type': 'object'},
            annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True,
                destructive_hint=False, open_world_hint=False)) for n in TOOLS | EXTRA])

    async def call_tool(self, name, arguments, **kwargs):
        assert name == 'game_status' and arguments == {}
        return CallToolResult(content=[], structured_content={'session_id': self.session,
            'fresh': True, 'live': True, 'demo': False})


def wire(kind, session, request_id, chat=None, text=None):
    rows = ['protocol=2', 'request_id=' + request_id, 'action=' + kind, 'session_id=' + session]
    if chat is not None:
        rows.append('chat_id=' + chat)
    if text is not None:
        rows.append('text=' + base64.b64encode(text.encode()).decode('ascii'))
    return action(('\n'.join(rows) + '\n').encode('ascii'))


async def worker(directory, stage, resume, candidate=False):
    # Refuse normal state/history paths even if the private worker flag is supplied manually.
    if (stage not in STAGES or directory.resolve() != directory or
            directory.parent != ((ROOT / 'runtime').resolve() if candidate else Path(tempfile.gettempdir()).resolve()) or
            not directory.name.startswith('syx-chat-process-') or
            not directory.is_dir() or directory.stat().st_uid != os.getuid() or
            directory.stat().st_mode & 0o777 != 0o700):
        raise ValueError('Owned private temporary worker directory required')
    history = directory / 'history'
    if resume:
        data = json.loads((directory / 'scenario.json').read_text())
    else:
        data = {'session': str(uuid4()), 'request': str(uuid4())}
    store = ChatStore(history, recover=resume)
    try:
        if not resume:
            data['chat'] = store.new(data['session'], model='deepseek-v4-pro')['chat_id']
            (directory / 'scenario.json').write_text(json.dumps(data))
        cid, session, rid = data['chat'], data['session'], data['request']
        mcp = SyntheticMCP(session)
        if candidate:
            from dev.chat_recovery_candidate import RecoveryCoordinator
            coordinator = RecoveryCoordinator(store, mcp, directory, 'synthetic-noncredential')
        else:
            coordinator = Coordinator(store, mcp, directory, 'synthetic-noncredential', simple=True)
        original = wire('send', session, rid, cid, QUESTION)
        calls = []

        def ready():
            marker = directory / 'ready.tmp'
            marker.write_text(json.dumps({'stage': stage, 'pid': os.getpid()}))
            marker.replace(directory / 'ready.json')

        class FakeProvider:
            async def complete(self, messages, tools, emit):
                assert len(tools) == 21
                calls.append(deepcopy(messages))
                if not resume and stage == 'streaming_partial':
                    emit(PARTIAL)
                    assert coordinator.partial[cid] == PARTIAL
                    coordinator.write_ui()
                    ready()
                    await asyncio.Future()
                emit(FINAL)
                return {'role': 'assistant', 'content': FINAL}

            async def close(self):
                pass

        def factory(chat):
            assert resume_allowed or not resume, 'Restart/replay must not invoke inference'
            return FakeProvider()

        resume_allowed = False
        instructions = coordinator.loop.instructions
        coordinator.loop = BlueprintConversation(store, mcp, factory)
        coordinator.loop.instructions = instructions
        if not resume:
            if stage == 'admitted_before_turn':
                async def hold_current_game(requested):
                    assert requested == session
                    assert store.db.execute('SELECT 1 FROM actions WHERE request_id=?', (rid,)).fetchone()
                    assert store.turns(cid) == [] and not calls
                    ready()
                    await asyncio.Future()
                coordinator.current_game = hold_current_game
            await coordinator.dispatch(original)
            await coordinator.tasks[cid]
            assert stage == 'completed_before_ui'
            assert store.turns(cid)[0]['status'] == 'completed' and len(calls) == 1
            # No UI write/ack after the task completes: the parent kills this owned process.
            assert not (directory / 'chat-ui.txt').exists()
            ready()
            await asyncio.Future()
        else:
            expected = {'admitted_before_turn': [], 'streaming_partial': ['interrupted'],
                        'completed_before_ui': ['completed']}[stage]
            assert [t['status'] for t in store.turns(cid)] == expected
            before_turns, before_events = store.turns(cid), store.events(cid)
            assert len([e for e in before_events if e['kind'] == 'assistant']) == (stage == 'completed_before_ui')
            assert not any(e['kind'] in {'turn_error', 'turn_cancelled'} for e in before_events)
            # Replay the old request before automatic current-load selection.
            await coordinator.dispatch(original)
            assert coordinator.ack == rid and coordinator.selected is None
            assert not coordinator.tasks and not calls
            assert store.turns(cid) == before_turns and store.events(cid) == before_events
            await coordinator.dispatch(wire('sync', session, str(uuid4())))
            assert coordinator.selected == cid and not calls
            coordinator.write_ui()
            rows = (directory / 'chat-ui.txt').read_text().splitlines()
            preview = '\n'.join(base64.b64decode(r[5:]).decode() for r in rows if r.startswith('line='))
            assert 'running=false' in rows and PARTIAL not in preview
            assert (FINAL in preview) == (stage == 'completed_before_ui')
            recovery_message = ''
            if candidate:
                from dev.chat_recovery_candidate import INTERRUPTED, UNKNOWN
                recovery_message = {'admitted_before_turn': UNKNOWN, 'streaming_partial': INTERRUPTED,
                                    'completed_before_ui': ''}[stage]
                assert coordinator.recovery_notice() == recovery_message
                notice = next(base64.b64decode(r[7:]).decode() for r in rows if r.startswith('notice='))
                assert notice == coordinator.notice + (' ' + recovery_message if recovery_message else '')
            # A genuinely new explicit request can proceed with fresh provider context.
            resume_allowed = True
            new_id = str(uuid4())
            await coordinator.dispatch(wire('send', session, new_id, cid, 'Synthetic explicit new request'))
            await coordinator.tasks[cid]
            assert len(calls) == 1 and store.turns(cid)[-1]['status'] == 'completed'
            assert [t['status'] for t in store.turns(cid)][:-1] == expected
            messages = calls[0]
            assert not any(m['role'] in {'assistant', 'tool'} for m in messages)
            history_text = messages[1]['content']
            assert (QUESTION in history_text) == (stage != 'admitted_before_turn')
            assert (FINAL in history_text) == (stage == 'completed_before_ui')
            assert PARTIAL not in history_text
            if candidate:
                assert coordinator.recovery_notice() == ''
                coordinator.write_ui()
                new_notice = next(base64.b64decode(r[7:]).decode() for r in
                    (directory / 'chat-ui.txt').read_text().splitlines() if r.startswith('notice='))
                assert INTERRUPTED not in new_notice and UNKNOWN not in new_notice
            return {'stage': stage, 'candidate_notice_round_trip_verified': candidate,
                'recovery_message': recovery_message, 'recovered_original_statuses': expected,
                'old_action_acknowledged_without_new_turn_or_provider': True,
                'automatic_sync_selected_original_chat': True,
                'new_explicit_turn_completed_with_fresh_context': True,
                'new_fake_provider_calls': len(calls), 'volatile_partial_not_recovered': True,
                'completed_answer_retained': stage == 'completed_before_ui',
                'admission_gap_has_no_turn': stage == 'admitted_before_turn'}
    finally:
        store.close()


def run_case(stage, *, candidate=False):
    if stage not in STAGES:
        raise ValueError('Unknown fixed crash stage')
    # Explicit environment avoids passing provider/auth variables into either child.
    env = {k: os.environ[k] for k in ('PATH', 'LANG', 'LC_ALL', 'SYSTEMROOT') if k in os.environ}
    with tempfile.TemporaryDirectory(prefix='syx-chat-process-', dir=ROOT / 'runtime' if candidate else None) as name:
        directory = Path(name)
        args = [sys.executable, str(Path(__file__).resolve()), '--worker', str(directory), '--stage', stage]
        if candidate:
            args.append('--candidate')
        child = subprocess.Popen(args, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 20
            while not (directory / 'ready.json').exists():
                if child.poll() is not None:
                    out, err = child.communicate()
                    raise AssertionError('Crash worker exited before checkpoint: ' + err.decode()[-3000:])
                if time.monotonic() >= deadline:
                    raise TimeoutError('Crash worker checkpoint exceeded 20 seconds')
                time.sleep(.02)
            marker = json.loads((directory / 'ready.json').read_text())
            assert marker == {'stage': stage, 'pid': child.pid}
            child.kill()  # Only the subprocess created by this invocation, never a discovered process.
            out, err = child.communicate(timeout=5)
            assert child.returncode == -9 and not out and not err
        finally:
            if child.poll() is None:
                child.kill()
                child.communicate(timeout=5)
        restarted = subprocess.run(args + ['--resume'], cwd=ROOT, env=env,
            capture_output=True, timeout=20)
        assert restarted.returncode == 0, restarted.stderr.decode()[-3000:]
        assert not restarted.stderr
        result = json.loads(restarted.stdout)
        return dict(result, owned_child_sigkill_verified=True, separate_resume_process=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--stage', choices=STAGES, help=argparse.SUPPRESS)
    parser.add_argument('--resume', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--candidate', action='store_true', help='Use the developer recovery-notice coordinator')
    args = parser.parse_args()
    if args.worker:
        result = asyncio.run(worker(args.worker, args.stage, args.resume, args.candidate))
        if args.resume:
            print(json.dumps(result))
    else:
        report = {'passed': True, 'candidate_notices': args.candidate, 'cases': [run_case(stage, candidate=args.candidate) for stage in STAGES],
            'source_sha256': {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in SOURCES},
            'external_inference_calls': 0, 'production_changed': False,
            'limits': ['Owned helper-process SIGKILL on this Linux host, not power loss or filesystem durability proof.',
                'Synthetic 21-tool MCP schema/status and fake inference; no native game, stdio transport or paid provider.',
                'Admission-before-turn gap is durably acknowledged without a turn; volatile streaming fragments are lost.',
                'Interrupted database status is verified; existing simple UI has no dedicated crash-recovery notice.',
                'A new explicit request has a new ID. No automatic resubmission, billing guarantee, badge or display proof.']}
        if args.candidate:
            report['limits'].append('Candidate IPC2 plain notice verified in a separate helper process; no native readability, peer review or player release acceptance.')
        raw = json.dumps(report, indent=2) + '\n'
        if args.output:
            args.output.write_text(raw)
        else:
            print(raw)
