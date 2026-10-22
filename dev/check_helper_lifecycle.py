"""Production helper entry point/lock/stdio restart with authored state and no key.

Linux/POSIX developer regression. Only task-created helpers and their directly observed stdio child are signaled.
No game, fake provider, credentials, paid inference or ordinary history is used.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import mcp.client.stdio as stdio_module
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from syx_chat_store import ChatStore
from syx_chat_service import b64

SOURCES = ['dev/check_helper_lifecycle.py', 'syx_chat_service.py', 'syx_chat_store.py',
           'syx_mcp.py', 'syx_chat.py', 'syx_blueprint_chat.py', 'syx_knowledge.py', 'snapshot.example.json']


class OwnedHelper:
    def __init__(self, state, history, scratch, label):
        self.state = state
        self.mcp_pid = None
        self.log_path = scratch.parent / (label + '.log')
        self.log = self.log_path.open('wb')
        env = {k: os.environ[k] for k in ('PATH', 'LANG', 'LC_ALL') if k in os.environ}
        self.process = subprocess.Popen([sys.executable, '-m', 'syx_chat_service',
            '--state-dir', str(state), '--history-dir', str(history)], cwd=ROOT, env=env,
            stdin=subprocess.DEVNULL, stdout=self.log, stderr=subprocess.STDOUT, start_new_session=True)

    def capture_mcp_child(self):
        # Kernel process metadata only, scoped to this task-owned parent; no args,
        # environment, process memory or unrelated process discovery.
        raw = subprocess.check_output(['ps', '-o', 'pid=', '--ppid', str(self.process.pid)], text=True)
        children = [int(row) for row in raw.split()]
        assert len(children) == 1
        self.mcp_pid = children[0]
        assert os.getpgid(self.mcp_pid) == self.mcp_pid  # Installed SDK starts a separate session.

    def close(self, *, interrupt_transport=False):
        if interrupt_transport:
            assert self.mcp_pid is not None
            os.kill(self.mcp_pid, signal.SIGKILL)
        try:
            if self.process.poll() is None:
                # Let the production async context reap/close its MCP child. That
                # child has its own SDK-created session, outside our helper group.
                os.kill(self.process.pid, signal.SIGINT)
            self.process.wait(timeout=15)
            if self.mcp_pid is not None:
                try:
                    os.kill(self.mcp_pid, 0)
                except ProcessLookupError:
                    pass
                else:
                    raise AssertionError('Owned MCP child was not reaped by production helper shutdown')
        finally:
            if self.process.poll() is None:
                os.killpg(self.process.pid, signal.SIGKILL)
                if self.mcp_pid is not None:
                    try:
                        os.kill(self.mcp_pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                self.process.wait(timeout=5)
            self.log.close()


def fields(state):
    try:
        raw = (state / 'chat-ui.txt').read_text('ascii')
    except FileNotFoundError:
        return {}
    assert len(raw.encode()) <= 240000
    return dict(row.split('=', 1) for row in raw.splitlines() if '=' in row and not row.startswith(('line=', 'chat=', 'current_chat=')))


def request(state, kind, session, *, chat=None, text=None):
    rid = str(uuid4())
    rows = ['protocol=2', 'request_id=' + rid, 'action=' + kind, 'session_id=' + session]
    if chat:
        rows.append('chat_id=' + chat)
    if text is not None:
        rows.append('text=' + b64(text))
    pending = state / 'action.pending'
    pending.write_text('\n'.join(rows) + '\n', encoding='ascii')
    pending.replace(state / 'chat-action.txt')
    return rid


def run():
    if os.name != 'posix':
        raise ValueError('This bounded process-group fixture requires POSIX')
    with tempfile.TemporaryDirectory(dir=ROOT / 'runtime', prefix='helper-lifecycle-') as name:
        directory = Path(name)
        state, history, scratch = [directory / n for n in ('state', 'history', 'scratch')]
        for path in (state, scratch):
            path.mkdir(mode=0o700)
        snapshot = json.loads((ROOT / 'snapshot.example.json').read_text())
        session = str(uuid4())
        snapshot['session_id'] = session
        # Authored positive admission control, never a native/world observation.
        # Retain the original DEMO-unverified version and synthetic data qualifiers.
        snapshot['demo'] = False
        def heartbeat():
            snapshot['captured_at'] = datetime.now(timezone.utc).isoformat()
            pending = state / 'snapshot.pending'
            pending.write_text(json.dumps(snapshot), encoding='utf-8')
            pending.replace(state / 'snapshot.json')
        def wait(helper, predicate):
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                heartbeat()
                if helper.process.poll() is not None:
                    raise AssertionError('Owned helper exited before expected IPC checkpoint')
                frame = fields(state)
                if predicate(frame):
                    return frame
                time.sleep(.05)
            raise TimeoutError('Production helper IPC checkpoint exceeded 20 seconds')
        store = ChatStore(history)
        chat = store.new(session, 'Authored lifecycle fixture', model='deepseek-v4-pro')['chat_id']
        first_turn = str(uuid4())
        store.begin(chat, first_turn, session, 'Authored initial running row; no inference')
        store.close()
        heartbeat()
        first = OwnedHelper(state, history, scratch, 'first')
        contender = second = None
        try:
            initial = wait(first, lambda f: f.get('protocol') == '2')
            assert initial['connected'] == 'false'
            first.capture_mcp_child()
            sync = request(state, 'sync', session)
            wait(first, lambda f: f.get('request_id') == sync and f.get('chat_id') == chat)
            store = ChatStore(history)
            try:
                assert [t['status'] for t in store.turns(chat)] == ['interrupted']
                live_turn = str(uuid4())
                store.begin(chat, live_turn, session, 'Authored running row while first helper owns the lock; no inference')
                before = store.turns(chat), store.events(chat)
                contender_state = directory / 'contender-state'
                contender = OwnedHelper(contender_state, history, scratch, 'contender')
                deadline = time.monotonic() + 20
                while contender.process.poll() is None and time.monotonic() < deadline:
                    heartbeat()
                    time.sleep(.05)
                assert contender.process.poll() is not None and contender.process.returncode != 0
                assert 'A coordinator already owns this history directory' in contender.log_path.read_text()
                assert (store.turns(chat), store.events(chat)) == before
                assert store.turns(chat)[1]['status'] == 'running'  # Lock refusal precedes recover=True.
            finally:
                store.close()
            first.close(interrupt_transport=True)
            assert first.process.returncode is not None
            second = OwnedHelper(state, history, scratch, 'second')
            assert second.process.pid != first.process.pid
            # Old sync remains in the action file. Ack alone cannot restore selection.
            frame = wait(second, lambda f: f.get('request_id') == sync and 'chat_id' not in f)
            assert frame['connected'] == 'false'
            new_sync = request(state, 'sync', session)
            frame = wait(second, lambda f: f.get('request_id') == new_sync and f.get('chat_id') == chat)
            assert frame['running'] == 'false' and frame['connected'] == 'false'
            second.capture_mcp_child()
            assert second.mcp_pid != first.mcp_pid
            store = ChatStore(history)
            try:
                assert [t['status'] for t in store.turns(chat)] == ['interrupted', 'interrupted']
                before = store.turns(chat), store.events(chat)
                send = request(state, 'send', session, chat=chat, text='Authored keyless Send must be rejected')
                frame = wait(second, lambda f: f.get('request_id') == send)
                notice = base64.b64decode(frame['notice'], validate=True).decode()
                assert 'DeepSeek API key is missing; no request sent' in notice
                assert (store.turns(chat), store.events(chat)) == before
                # Reopening the action file is not an automatic retry; the durable journal remains.
                assert store.db.execute('SELECT 1 FROM actions WHERE request_id=?', (send,)).fetchone()
                assert len(store.list(session, simple=True)) == 1
            finally:
                store.close()
            return {'passed': True, 'production_entrypoint_invocations': 3,
                'successful_helper_and_stdio_mcp_startups': 2,
                'history_lock_contender_refused_before_recovery': True,
                'live_authored_turn_preserved_on_lock_refusal': True,
                'owned_stdio_mcp_abruptly_terminated': True,
                'helper_stopped_with_interrupt_if_needed': True,
                'owned_mcp_child_reaped_before_restart': True,
                'restarted_helper_pid_changed': True,
                'old_sync_acknowledgement_did_not_select_chat': True,
                'new_sync_selected_persisted_chat_through_actual_mcp': True,
                'startup_recovered_authored_running_rows': 2,
                'missing_key_send_rejected_without_turn_or_event': True,
                'provider_key_configured': False, 'external_inference_calls': 0,
                'native_game_used': False, 'production_changed': False,
                'mcp_distribution_version': version('mcp'),
                'installed_stdio_module_sha256': hashlib.sha256(Path(stdio_module.__file__).read_bytes()).hexdigest(),
                'source_sha256': {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in SOURCES},
                'limits': ['Authored snapshot with demo admission flag cleared, original DEMO-unverified version/qualifiers retained; no native game truth.',
                    'Two authored running history rows without provider tasks, not interrupted paid streams or billing evidence.',
                    'SIGKILL of the directly observed task-owned MCP child, then SIGINT to the helper if needed for production async cleanup/reaping. Not abrupt helper death, every crash timing or power loss.',
                    'Actual production helper entry point, file IPC, lock, SQLite startup recovery and stdio MCP restart; no native UI/draft/visibility/readability proof.',
                    'No credential environment or env-file option supplied. The production missing-key guard rejects Send before inference.']}
        finally:
            for helper in (contender, second, first):
                if helper is not None and not helper.log.closed:
                    helper.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    raw = json.dumps(run(), indent=2) + '\n'
    if args.output:
        args.output.write_text(raw)
    else:
        print(raw)
