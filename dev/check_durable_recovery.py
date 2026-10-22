"""Owned-process durable uncertainty checks; no game, MCP, key or inference."""
import argparse
import asyncio
import base64
import hashlib
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
from dev.chat_durable_recovery_candidate import DurableRecoveryCoordinator
from dev.chat_recovery_candidate import UNKNOWN
from dev.check_chat_process_recovery import wire
from syx_chat_store import ChatStore, identity

SOURCES = ('dev/check_durable_recovery.py', 'dev/chat_durable_recovery_candidate.py',
           'dev/chat_recovery_candidate.py', 'syx_chat_service.py', 'syx_chat_store.py')


def owned_directory(directory):
    path = Path(directory)
    if (path.resolve() != path or path.parent != ROOT / 'runtime' or
            not path.name.startswith('durable-recovery-process-') or not path.is_dir() or
            path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o777 != 0o700):
        raise ValueError('Owned private runtime worker directory required')
    return path


def ui_notice(directory):
    line = next(row for row in (directory / 'chat-ui.txt').read_text().splitlines() if row.startswith('notice='))
    return base64.b64decode(line[7:], validate=True).decode('utf-8')


def worker(directory, stage):
    directory = owned_directory(directory)
    config = json.loads((directory / 'config.json').read_text())
    session, chat, rid = (identity(config[key]) for key in ('session', 'chat', 'request'))
    store = ChatStore(directory / 'history')
    try:
        c = DurableRecoveryCoordinator(store, None, directory, '')
        c.selected = chat
        before = store.events(chat), store.turns(chat)
        if stage == 'observe':
            assert c.recovery_notice() == ''
            asyncio.run(c.dispatch(wire('send', session, rid, chat, 'Synthetic duplicate')))
            assert c.recovery_notice() == UNKNOWN and c.ack == rid
            assert (store.events(chat), store.turns(chat)) == before
            c.write_ui()
            assert UNKNOWN in ui_notice(directory)
            result = {'observed_unknown_committed': True, 'no_history_turn_or_event_added': True}
        elif stage == 'restore_clear':
            # No replay or action dispatch occurs in this new process.
            assert c.ack == '' and c.recovery_notice() == UNKNOWN
            assert (store.events(chat), store.turns(chat)) == before
            c.write_ui()
            assert UNKNOWN in ui_notice(directory)
            store.begin(chat, str(uuid4()), session, 'Authored later state, no inference')
            assert c.recovery_notice() == ''
            assert store.db.execute('SELECT count(*) FROM candidate_unknown_sends').fetchone() == (0,)
            result = {'unknown_restored_without_dispatch': True,
                      'later_authored_turn_clears_observation': True}
        else:
            assert stage == 'verify_clear'
            assert c.ack == '' and c.recovery_notice() == '' and not c.unknown_sends
            assert (store.events(chat), store.turns(chat)) == before
            c.write_ui()
            assert UNKNOWN not in ui_notice(directory)
            result = {'clearing_survives_third_process': True}
        assert c.tasks == {} and c.loop.context == {} and c.key == ''
        result.update(passed=True, inference_calls=0, provider_tasks=0)
        output = directory / (stage + '.json')
        temporary = directory / (stage + '.tmp')
        temporary.write_text(json.dumps(result))
        os.replace(temporary, output)
        if stage == 'observe':
            # Parent kills only this owned child after reading the committed marker.
            time.sleep(30)
    finally:
        store.close()


def check():
    with tempfile.TemporaryDirectory(dir=ROOT / 'runtime', prefix='durable-recovery-process-') as name:
        directory = Path(name).resolve()
        session, rid = str(uuid4()), str(uuid4())
        store = ChatStore(directory / 'history')
        chat = store.new(session, model='deepseek-v4-pro')['chat_id']
        DurableRecoveryCoordinator(store, None, directory, '')
        with store.db:
            store.db.execute('INSERT INTO actions(request_id) VALUES(?)', (rid,))
        store.close()
        (directory / 'config.json').write_text(json.dumps({'session': session, 'chat': chat, 'request': rid}))
        results = []
        # No inherited provider credentials or app tokens; no HOME reassignment.
        environment = {key: os.environ[key] for key in ('PATH', 'LANG', 'LC_ALL') if key in os.environ}
        for stage in ('observe', 'restore_clear', 'verify_clear'):
            with (directory / (stage + '.log')).open('wb') as log:
                child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()),
                    '--worker', str(directory), '--stage', stage], cwd=ROOT,
                    env=environment, stdout=log, stderr=subprocess.STDOUT)
                try:
                    output = directory / (stage + '.json')
                    deadline = time.monotonic() + 20
                    while not output.exists():
                        if child.poll() is not None or time.monotonic() > deadline:
                            raise AssertionError('Owned durable recovery worker did not complete its checkpoint')
                        time.sleep(0.02)
                    result = json.loads(output.read_text())
                    assert result['passed']
                    if stage == 'observe':
                        child.kill()
                        assert child.wait(timeout=5) == -signal.SIGKILL
                        result['owned_child_sigkill_after_committed_observation'] = True
                    else:
                        assert child.wait(timeout=5) == 0
                    results.append(result)
                finally:
                    if child.poll() is None:
                        child.kill()
                        child.wait(timeout=5)
        return {'passed': True, 'owned_processes': 3, 'checks': results,
            'external_inference_calls': 0, 'production_integrated': False,
            'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES},
            'limits': ['One observed duplicate, one post-commit owned-child SIGKILL and authored later history; not a pending paid request, all crash timings or power loss.',
                       'No native game, MCP transport, physical UI, concurrent writers or player-release acceptance.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output')
    parser.add_argument('--worker')
    parser.add_argument('--stage', choices=('observe', 'restore_clear', 'verify_clear'))
    args = parser.parse_args()
    if args.worker:
        if not args.stage or args.output:
            parser.error('Fixed worker stage required')
        worker(Path(args.worker), args.stage)
    else:
        if not args.output or args.stage:
            parser.error('--output required')
        Path(args.output).write_text(json.dumps(check(), indent=2) + '\n')
