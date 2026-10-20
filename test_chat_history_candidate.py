"""Disposable SQLite candidate tests; no provider, native game or real history."""
import importlib.util
from pathlib import Path
import sqlite3
from uuid import uuid4
import zipfile

import pytest

from dev.chat_history_candidate import HistoryCandidate
from syx_chat_store import ChatStore


def uid():
    return str(uuid4())


def chat(store, session=None, **kwargs):
    return store.new(session or uid(), model='deepseek-v4-pro', **kwargs)


def reply(store, c, text='Answer', status='completed', final=True):
    tid = uid()
    session = c['attached_session']
    store.begin(c['chat_id'], tid, session, 'Question')
    store.append(c['chat_id'], tid, session, 'assistant', {'text': text, 'completed': final})
    eid = store.events(c['chat_id'])[-1]['event_id']
    if status != 'running':
        store.finish(c['chat_id'], tid, status)
    return tid, eid


def test_explicit_migration_baselines_old_replies_but_not_pending_completion(tmp_path):
    with_store = ChatStore(tmp_path)
    c = chat(with_store)
    reply(with_store, c)
    pending, eid = reply(with_store, c, status='running')
    ux = HistoryCandidate(with_store)
    with pytest.raises(ValueError, match='initialization'):
        ux.unread(c['chat_id'])
    assert ux.initialize() is True and ux.unread(c['chat_id']) == []
    with_store.finish(c['chat_id'], pending, 'completed')
    assert ux.unread(c['chat_id'])[0]['event_id'] == eid
    assert ux.initialize() is False
    assert len(ux.unread(c['chat_id'])) == 1
    assert with_store.db.execute('PRAGMA user_version').fetchone()[0] == 1
    with_store.close()


def test_display_receipts_are_chat_session_and_event_scoped_atomic_and_durable(tmp_path):
    store = ChatStore(tmp_path)
    a, b = chat(store), chat(store)
    ux = HistoryCandidate(store)
    ux.initialize()
    _, ae = reply(store, a)
    _, be = reply(store, b)
    for events, session in [([ae, be], a['attached_session']), ([ae], b['attached_session']), ([uid()], a['attached_session'])]:
        with pytest.raises(ValueError, match='acknowledgement'):
            ux.acknowledge(a['chat_id'], session, events)
        assert len(ux.unread(a['chat_id'])) == 1
    assert ux.acknowledge(a['chat_id'], a['attached_session'], [ae, ae]) == 1
    assert ux.acknowledge(a['chat_id'], a['attached_session'], [ae]) == 0
    assert ux.unread(a['chat_id']) == [] and len(ux.unread(b['chat_id'])) == 1
    store.close()
    store = ChatStore(tmp_path, recover=True)
    assert HistoryCandidate(store).unread(a['chat_id']) == []
    assert len(HistoryCandidate(store).unread(b['chat_id'])) == 1
    store.close()


def test_partial_empty_failed_cancelled_and_interrupted_are_not_successful_unread(tmp_path):
    store = ChatStore(tmp_path)
    c = chat(store)
    ux = HistoryCandidate(store)
    ux.initialize()
    for text, status, final in [('partial', 'completed', False), ('', 'completed', True), ('  ', 'completed', True),
                                ('failed', 'failed', True), ('stop', 'cancelled', True), ('interrupted', 'running', True)]:
        reply(store, c, text, status, final)
    store.close()
    store = ChatStore(tmp_path, recover=True)
    assert HistoryCandidate(store).unread(c['chat_id']) == []
    store.close()


def test_ordinary_base_store_reopen_does_not_baseline_or_recover_live_turns(tmp_path):
    store = ChatStore(tmp_path)
    c = chat(store)
    HistoryCandidate(store).initialize()
    reply(store, c)
    pending, _ = reply(store, c, status='running')
    store.close()
    store = ChatStore(tmp_path, recover=False)
    assert store.turns(c['chat_id'])[-1] == {
        'turn_id': pending, 'game_session': c['attached_session'], 'status': 'running'}
    assert len(HistoryCandidate(store).unread(c['chat_id'])) == 1
    assert store.db.execute('SELECT count(*) FROM syx_ux_reads').fetchone()[0] == 0
    store.close()


def test_utf8_budget_accepts_exact_bytes_and_refuses_smaller_complete_result(tmp_path):
    store = ChatStore(tmp_path)
    c = chat(store)
    ux = HistoryCandidate(store)
    ux.initialize()
    reply(store, c, text='猫' * 10)
    raw = store.db.execute("SELECT payload FROM events WHERE kind='assistant'").fetchone()[0]
    assert len(raw.encode('utf-8')) > len(raw)
    ux.BYTE_CAP = len(raw.encode('utf-8'))
    ux.ROW_CAP = 1
    assert len(ux.unread(c['chat_id'])) == 1
    ux.BYTE_CAP -= 1
    with pytest.raises(ValueError, match='budget'):
        ux.unread(c['chat_id'])
    store.close()


def test_out_of_order_completion_and_duplicate_final_events_count_once(tmp_path):
    store = ChatStore(tmp_path)
    c = chat(store)
    ux = HistoryCandidate(store)
    ux.initialize()
    early, early_event = reply(store, c, status='running')
    later, later_event = reply(store, c)
    ux.acknowledge(c['chat_id'], c['attached_session'], [later_event])
    store.finish(c['chat_id'], early, 'completed')
    assert [r['event_id'] for r in ux.unread(c['chat_id'])] == [early_event]
    ux.acknowledge(c['chat_id'], c['attached_session'], [early_event])
    store.append(c['chat_id'], later, c['attached_session'], 'assistant', {'text': 'Duplicate', 'completed': True})
    assert ux.unread(c['chat_id']) == []
    store.close()


def test_deleted_event_sequence_reuse_cannot_clear_another_chat(tmp_path):
    store = ChatStore(tmp_path)
    ux = HistoryCandidate(store)
    ux.initialize()
    a = chat(store)
    _, old_id = reply(store, a)
    old_seq = store.events(a['chat_id'])[-1]['sequence']
    ux.acknowledge(a['chat_id'], a['attached_session'], [old_id])
    store.delete(a['chat_id'])
    b = chat(store)
    reply(store, b)
    assert store.events(b['chat_id'])[-1]['sequence'] == old_seq
    with pytest.raises(ValueError):
        ux.acknowledge(b['chat_id'], b['attached_session'], [old_id])
    assert len(ux.unread(b['chat_id'])) == 1
    assert store.db.execute('PRAGMA foreign_key_check').fetchall() == []
    store.close()


def test_initialization_failure_rolls_back_schema_and_baseline(tmp_path):
    store = ChatStore(tmp_path)
    c = chat(store)
    reply(store, c)
    before = store.events(c['chat_id'])
    store.db.set_authorizer(lambda op, a, b, db, source:
        sqlite3.SQLITE_DENY if op == sqlite3.SQLITE_INSERT and a == 'syx_ux_reads' else sqlite3.SQLITE_OK)
    with pytest.raises(sqlite3.DatabaseError):
        HistoryCandidate(store).initialize()
    store.db.set_authorizer(None)
    assert store.db.execute("SELECT name FROM sqlite_master WHERE name LIKE 'syx_ux_%'").fetchall() == []
    assert store.events(c['chat_id']) == before
    assert store.db.execute('PRAGMA user_version').fetchone()[0] == 1
    assert HistoryCandidate(store).initialize()
    store.close()


@pytest.mark.parametrize('bundle', ['latest-user-test.zip', 'previous-user-test.zip'])
def test_actual_bundled_legacy_store_can_open_recover_create_delete_and_return(tmp_path, bundle):
    root = Path(__file__).resolve().parent
    with zipfile.ZipFile(root/'releases'/bundle) as z:
        old_source = z.read('syx_chat_store.py')
    module_path = tmp_path/'legacy_store.py'
    module_path.write_bytes(old_source)
    spec = importlib.util.spec_from_file_location('legacy_store', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    history = tmp_path/'history'
    store = ChatStore(history)
    a = chat(store)
    ux = HistoryCandidate(store)
    ux.initialize()
    _, ae = reply(store, a)
    ux.acknowledge(a['chat_id'], a['attached_session'], [ae])
    reply(store, a, status='running')
    store.close()
    legacy = module.ChatStore(history, recover=True)
    assert legacy.turns(a['chat_id'])[-1]['status'] == 'interrupted'
    b = chat(legacy)
    reply(legacy, b)
    legacy.delete(a['chat_id'])
    assert legacy.db.execute('PRAGMA foreign_key_check').fetchall() == []
    legacy.close()
    store = ChatStore(history)
    ux = HistoryCandidate(store)
    assert ux.initialize() is False
    assert len(ux.unread(b['chat_id'])) == 1
    store.close()


def test_history_and_pro_filters_apply_before_limit_and_preserve_old_session(tmp_path):
    store = ChatStore(tmp_path)
    session = uid()
    c = chat(store, session)
    reply(store, c)
    new_session = uid()
    store.attach(c['chat_id'], new_session)
    for _ in range(105):
        chat(store)
    ux = HistoryCandidate(store)
    assert ux.chats(session=session, scope='attached') == []
    assert [r['chat_id'] for r in ux.chats(session=session, scope='history')] == [c['chat_id']]
    store.db.execute("UPDATE chats SET model='deepseek-flash' WHERE chat_id<>?", (c['chat_id'],))
    store.db.commit()
    assert [r['chat_id'] for r in ux.chats()] == [c['chat_id']]
    assert len(ux.chats(simple=False)) == 100
    store.close()


def test_scan_refusal_unknown_versions_nested_transactions_and_limits(tmp_path):
    store = ChatStore(tmp_path)
    c = chat(store)
    ux = HistoryCandidate(store)
    ux.initialize()
    _, eid = reply(store, c)
    ux.ROW_CAP = 0
    with pytest.raises(ValueError, match='budget'):
        ux.unread(c['chat_id'])
    ux.ROW_CAP = 10000
    ux.BYTE_CAP = 1
    with pytest.raises(ValueError, match='budget'):
        ux.acknowledge(c['chat_id'], c['attached_session'], [eid])
    ux.BYTE_CAP = 2 * 1024 * 1024
    assert len(ux.unread(c['chat_id'])) == 1
    for ids in [[], [eid]*101, eid]:
        with pytest.raises(ValueError):
            ux.acknowledge(c['chat_id'], c['attached_session'], ids)
    store.db.execute('BEGIN')
    with pytest.raises(ValueError, match='nested'):
        ux.initialize()
    store.db.rollback()
    store.db.execute('UPDATE syx_ux_schema SET version=2')
    store.db.commit()
    with pytest.raises(ValueError, match='version'):
        ux.initialize()
    assert store.db.execute('SELECT count(*) FROM syx_ux_reads').fetchone()[0] == 0
    store.close()
