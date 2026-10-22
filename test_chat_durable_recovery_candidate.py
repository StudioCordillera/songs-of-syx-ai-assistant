"""Durable uncertainty observations, separate from provider/delivery acceptance."""
import asyncio
from pathlib import Path
import sqlite3
import tempfile
from uuid import uuid4

import pytest

from dev.chat_durable_recovery_candidate import DurableRecoveryCoordinator
from dev.chat_recovery_candidate import UNKNOWN
from dev.check_chat_process_recovery import wire
from syx_chat_store import ChatStore

ROOT = Path(__file__).resolve().parent
uid = lambda: str(uuid4())


@pytest.fixture
def candidate():
    with tempfile.TemporaryDirectory(dir=ROOT / 'runtime', prefix='durable-notice-test-') as name:
        directory = Path(name)
        store = ChatStore(directory / 'history')
        session = uid()
        chat = store.new(session, model='deepseek-v4-pro')['chat_id']
        c = DurableRecoveryCoordinator(store, None, directory, '')
        c.selected = chat
        try:
            yield c, store, directory, session, chat
        finally:
            store.close()


def observe(c, store, session, chat):
    rid = uid()
    with store.db:
        store.db.execute('INSERT INTO actions(request_id) VALUES(?)', (rid,))
    asyncio.run(c.dispatch(wire('send', session, rid, chat, 'Synthetic replay')))
    return rid


def test_unknown_observation_survives_reopen_without_replaying_request(candidate):
    c, store, directory, session, chat = candidate
    observe(c, store, session, chat)
    assert c.recovery_notice() == UNKNOWN
    before = store.events(chat), store.turns(chat)
    reopened = ChatStore(store.directory)
    try:
        again = DurableRecoveryCoordinator(reopened, None, directory, '')
        again.selected = chat
        assert again.ack == '' and again.tasks == {}
        assert again.recovery_notice() == UNKNOWN
        assert (reopened.events(chat), reopened.turns(chat)) == before
        assert reopened.db.execute('PRAGMA user_version').fetchone() == (1,)
    finally:
        reopened.close()


def test_admission_without_an_observed_duplicate_does_not_invent_unknown(candidate):
    c, store, directory, session, chat = candidate
    with store.db:
        store.db.execute('INSERT INTO actions(request_id) VALUES(?)', (uid(),))
    again = DurableRecoveryCoordinator(store, None, directory, '')
    again.selected = chat
    assert again.recovery_notice() == '' and not again.unknown_sends


def test_later_durable_turn_clears_observation_across_reopen(candidate):
    c, store, directory, session, chat = candidate
    observe(c, store, session, chat)
    turn = uid()
    store.begin(chat, turn, session, 'New authored turn')
    store.finish(chat, turn, 'completed')
    assert c.recovery_notice() == '' and not c.unknown_sends
    again = DurableRecoveryCoordinator(store, None, directory, '')
    again.selected = chat
    assert again.recovery_notice() == '' and not again.unknown_sends


def test_old_latest_turn_is_compared_without_reassigning_historical_session(candidate):
    c, store, directory, session, chat = candidate
    turn = uid()
    store.begin(chat, turn, session, 'Earlier turn')
    store.finish(chat, turn, 'completed')
    observe(c, store, session, chat)
    new_session = uid()
    store.attach(chat, new_session, explicit=False)
    again = DurableRecoveryCoordinator(store, None, directory, '')
    again.selected = chat
    assert again.recovery_notice() == UNKNOWN
    assert store.turns(chat)[0]['game_session'] == session


def test_unknown_eviction_order_is_durable_and_reobservation_refreshes_it(candidate):
    c, store, directory, session, chat = candidate
    chats = [chat] + [store.new(session, model='deepseek-v4-pro')['chat_id'] for _ in range(100)]
    for cid in chats[:100]:
        observe(c, store, session, cid)
    observe(c, store, session, chats[0])
    observe(c, store, session, chats[100])
    again = DurableRecoveryCoordinator(store, None, directory, '')
    assert len(again.unknown_sends) == 100
    assert chats[0] in again.unknown_sends and chats[1] not in again.unknown_sends
    assert list(again.unknown_sends)[-1] == chats[100]
    assert store.db.execute('SELECT count(*) FROM candidate_unknown_sends').fetchone() == (100,)


def test_deleted_chat_cascades_observation(candidate):
    c, store, directory, session, chat = candidate
    observe(c, store, session, chat)
    store.delete(chat)
    again = DurableRecoveryCoordinator(store, None, directory, '')
    assert not again.unknown_sends


def test_unchanged_refresh_does_not_rewrite_observations(candidate):
    c, store, directory, session, chat = candidate
    observe(c, store, session, chat)
    changes = store.db.total_changes
    for _ in range(5):
        assert c.recovery_notice() == UNKNOWN
    assert store.db.total_changes == changes


def test_failed_persistence_rolls_back_eviction_and_restores_memory(candidate):
    c, store, directory, session, chat = candidate
    observe(c, store, session, chat)
    before = c.unknown_sends.copy()
    with store.db:
        store.db.execute("CREATE TRIGGER fixed_write_failure BEFORE INSERT ON candidate_unknown_sends BEGIN SELECT RAISE(ABORT,'Fixed observation failure'); END")
    other = store.new(session, model='deepseek-v4-pro')['chat_id']
    with pytest.raises(sqlite3.IntegrityError, match='Fixed observation failure'):
        observe(c, store, session, other)
    assert c.unknown_sends == before
    assert c._load_unknown() == before
    assert not c.tasks and store.turns(other) == []
    assert store.db.execute('SELECT count(*) FROM candidate_unknown_sends').fetchone() == (1,)


def test_external_state_path_is_refused_before_candidate_table(tmp_path):
    store = ChatStore(tmp_path / 'history')
    try:
        with pytest.raises(ValueError):
            DurableRecoveryCoordinator(store, None, tmp_path, '')
        assert store.db.execute("SELECT name FROM sqlite_master WHERE name='candidate_unknown_sends'").fetchone() is None
    finally:
        store.close()


@pytest.mark.parametrize('field,value', [('previous_turn_id', 'not-a-uuid'), ('previous_status', None)])
def test_malformed_persisted_observation_is_refused(candidate, field, value):
    c, store, directory, session, chat = candidate
    turn = uid()
    store.begin(chat, turn, session, 'Earlier')
    store.finish(chat, turn, 'completed')
    observe(c, store, session, chat)
    # Fixed corruption setup, not an accepted writer or repair path.
    store.db.execute('PRAGMA ignore_check_constraints=ON')
    with store.db:
        store.db.execute('UPDATE candidate_unknown_sends SET '+field+'=?', (value,))
    with pytest.raises(ValueError):
        DurableRecoveryCoordinator(store, None, directory, '')


def test_owned_process_kill_restore_and_durable_clear():
    from dev.check_durable_recovery import check
    result = check()
    assert result['passed'] and result['owned_processes'] == 3
    assert result['external_inference_calls'] == 0
    assert result['checks'][0]['owned_child_sigkill_after_committed_observation']
    assert result['checks'][1]['unknown_restored_without_dispatch']
    assert result['checks'][2]['clearing_survives_third_process']


def test_finishing_old_turn_does_not_resolve_a_different_unknown_send(candidate):
    c, store, directory, session, chat = candidate
    turn = uid()
    store.begin(chat, turn, session, 'Older pending turn')
    observe(c, store, session, chat)
    assert c.recovery_notice() == UNKNOWN
    store.finish(chat, turn, 'completed')
    again = DurableRecoveryCoordinator(store, None, directory, '')
    again.selected = chat
    assert again.recovery_notice() == UNKNOWN
    assert again.unknown_sends[chat] == (turn, 'running')


def test_active_reply_suppresses_but_does_not_forget_durable_unknown(candidate):
    c, store, directory, session, chat = candidate
    observe(c, store, session, chat)
    async def scenario():
        task = asyncio.create_task(asyncio.sleep(30))
        c.tasks[chat] = task
        try:
            assert c.recovery_notice() == ''
            assert store.db.execute('SELECT count(*) FROM candidate_unknown_sends').fetchone() == (1,)
        finally:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        assert c.recovery_notice() == UNKNOWN
    asyncio.run(scenario())


def test_disabled_foreign_keys_refuse_without_silent_repair(candidate):
    c, store, directory, session, chat = candidate
    observe(c, store, session, chat)
    store.db.execute('PRAGMA foreign_keys=OFF')
    with pytest.raises(ValueError, match='requires enabled history foreign keys'):
        DurableRecoveryCoordinator(store, None, directory, '')
    assert store.db.execute('PRAGMA foreign_keys').fetchone() == (0,)
    assert store.db.execute('SELECT count(*) FROM candidate_unknown_sends').fetchone() == (1,)


def test_replayed_non_send_id_has_neutral_visible_wording(candidate):
    c, store, directory, session, chat = candidate
    original = wire('select', session, uid(), chat)
    asyncio.run(c.dispatch(original))
    other = store.new(session, model='deepseek-v4-pro')['chat_id']
    asyncio.run(c.dispatch(wire('send', session, original['request_id'], other, 'Different replay payload')))
    c.selected = other
    assert c.recovery_notice() == UNKNOWN
    assert 'Send' not in UNKNOWN and 'original outcome unknown' in UNKNOWN
    assert not c.tasks and store.turns(other) == []


def test_empty_base_notice_has_no_added_leading_space(candidate):
    import base64
    c, store, directory, session, chat = candidate
    observe(c, store, session, chat)
    c.notice = ''
    c.write_ui()
    encoded = next(row[7:] for row in (directory / 'chat-ui.txt').read_text().splitlines() if row.startswith('notice='))
    assert base64.b64decode(encoded, validate=True).decode() == UNKNOWN
    assert c.notice == ''
