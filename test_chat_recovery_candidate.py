"""Recovery notice semantics and bounds, separate from native display acceptance."""
import asyncio
import base64
from pathlib import Path
import tempfile
from uuid import uuid4
import pytest
from syx_chat_store import ChatStore
from dev.chat_recovery_candidate import RecoveryCoordinator, INTERRUPTED, UNKNOWN
from dev.check_chat_process_recovery import wire

ROOT = Path(__file__).resolve().parent
uid = lambda: str(uuid4())


@pytest.fixture
def candidate():
    with tempfile.TemporaryDirectory(dir=ROOT / 'runtime', prefix='recovery-notice-') as name:
        directory = Path(name)
        store = ChatStore(directory / 'history')
        session = uid()
        chat = store.new(session, model='deepseek-v4-pro')['chat_id']
        coordinator = RecoveryCoordinator(store, None, directory, 'synthetic-noncredential')
        coordinator.selected = chat
        try:
            yield coordinator, store, directory, session, chat
        finally:
            store.close()


def notice(directory):
    row = next(x for x in (directory / 'chat-ui.txt').read_text().splitlines() if x.startswith('notice='))
    return base64.b64decode(row[7:], validate=True).decode()


def test_notice_requires_disposable_state_and_history_before_journal(tmp_path):
    store = ChatStore(tmp_path / 'history')
    try:
        with pytest.raises(ValueError):
            RecoveryCoordinator(store, None, tmp_path, '')
        assert store.db.execute("SELECT name FROM sqlite_master WHERE name='actions'").fetchone() is None
    finally:
        store.close()


def test_interrupted_latest_turn_has_plain_notice_without_mutating_history(candidate):
    c, store, directory, session, chat = candidate
    store.begin(chat, uid(), session, 'Question')
    # Same production startup recovery, with the coordinator absent from inference.
    reopened = ChatStore(store.directory, recover=True)
    reopened.close()
    before = store.events(chat), store.turns(chat)
    c.notice = 'Connection unavailable'
    c.write_ui()
    assert notice(directory) == 'Connection unavailable ' + INTERRUPTED
    assert c.notice == 'Connection unavailable'
    c.write_ui()
    assert notice(directory).count(INTERRUPTED) == 1
    assert (store.events(chat), store.turns(chat)) == before
    assert c.tasks == {} and c.loop.context == {}
    other = store.new(session, model='deepseek-v4-pro')['chat_id']
    c.selected = other
    assert c.recovery_notice() == ''
    c.selected = chat
    store.begin(chat, uid(), session, 'New explicit question')
    assert c.recovery_notice() == ''


def test_duplicate_without_turn_warns_only_on_its_chat_and_later_turn_supersedes(candidate):
    c, store, directory, session, chat = candidate
    request = wire('send', session, uid(), chat, 'Original')
    with store.db:
        store.db.execute('INSERT INTO actions(request_id) VALUES(?)', (request['request_id'],))
    before = store.events(chat)
    asyncio.run(c.dispatch(request))
    assert c.ack == request['request_id'] and not c.tasks
    assert c.recovery_notice() == UNKNOWN
    assert store.events(chat) == before and store.turns(chat) == []
    c.write_ui()
    assert UNKNOWN in notice(directory)
    c.selected = store.new(session, model='deepseek-v4-pro')['chat_id']
    assert c.recovery_notice() == ''
    c.selected = chat
    turn = uid()
    store.begin(chat, turn, session, 'New explicit request')
    store.finish(chat, turn, 'completed')
    assert c.recovery_notice() == '' and chat not in c.unknown_sends


def test_completed_replay_never_warns_or_changes_history(candidate):
    c, store, directory, session, chat = candidate
    rid = uid()
    with store.db:
        store.db.execute('INSERT INTO actions(request_id) VALUES(?)', (rid,))
    store.begin(chat, rid, session, 'Original')
    store.finish(chat, rid, 'completed')
    before = store.events(chat), store.turns(chat)
    asyncio.run(c.dispatch(wire('send', session, rid, chat, 'Original')))
    assert c.recovery_notice() == '' and not c.unknown_sends and not c.tasks
    assert (store.events(chat), store.turns(chat)) == before


def test_unknown_cache_is_bounded_and_deleted_or_non_pro_chat_is_not_added(candidate):
    c, store, directory, session, chat = candidate
    async def replay(cid):
        rid = uid()
        with store.db:
            store.db.execute('INSERT INTO actions(request_id) VALUES(?)', (rid,))
        await c.dispatch(wire('send', session, rid, cid, 'Original'))
    async def scenario():
        for _ in range(101):
            cid = store.new(session, model='deepseek-v4-pro')['chat_id']
            await replay(cid)
        assert len(c.unknown_sends) == 100
        before = dict(c.unknown_sends)
        await replay(uid())
        await replay(store.new(session)['chat_id'])
        assert dict(c.unknown_sends) == before
    asyncio.run(scenario())


def test_write_failure_restores_base_notice(candidate, monkeypatch):
    c, store, directory, session, chat = candidate
    monkeypatch.setattr(c, 'recovery_notice', lambda: INTERRUPTED)
    def fail(self):
        raise OSError('Fixed failure')
    from syx_chat_service import Coordinator
    monkeypatch.setattr(Coordinator, 'write_ui', fail)
    original = c.notice
    with pytest.raises(OSError, match='Fixed failure'):
        c.write_ui()
    assert c.notice == original


def test_active_reply_suppresses_recovery_warning_until_it_finishes(candidate):
    c, store, directory, session, chat = candidate
    store.begin(chat, uid(), session, 'Earlier question')
    reopened = ChatStore(store.directory, recover=True)
    reopened.close()
    async def scenario():
        task = asyncio.create_task(asyncio.sleep(30))
        c.tasks[chat] = task
        try:
            assert c.recovery_notice() == ''
        finally:
            task.cancel()
            import contextlib
            with contextlib.suppress(asyncio.CancelledError):
                await task
        assert c.recovery_notice() == INTERRUPTED
    asyncio.run(scenario())


def test_disposable_state_with_external_history_is_refused_before_journal(tmp_path):
    store = ChatStore(tmp_path / 'history')
    try:
        with tempfile.TemporaryDirectory(dir=ROOT / 'runtime', prefix='recovery-notice-') as name:
            with pytest.raises(ValueError):
                RecoveryCoordinator(store, None, Path(name), '')
        assert store.db.execute("SELECT name FROM sqlite_master WHERE name='actions'").fetchone() is None
    finally:
        store.close()
