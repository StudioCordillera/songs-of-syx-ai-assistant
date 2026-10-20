"""Atomic acceptance on disposable real ChatStore histories; no dispatch/provider."""
import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import time
from uuid import uuid4

import pytest

from syx_chat_store import ChatStore
from dev.chat_target_queue import TargetQueue, TargetAdmission
from dev.chat_target_candidate import canonical
from dev.chat_history_candidate import HistoryCandidate
from test_syx_capture import capture_setup
from test_chat_target_candidate import targets


@pytest.fixture
def queued(targets, tmp_path):
    drafts, tokens, advisor, state, *_ = targets
    store = ChatStore(tmp_path / 'private-queue', secrets=('test-credential-must-not-persist',))
    chat = store.new(state['session_id'], model='deepseek-v4-pro')['chat_id']
    item = drafts.stage(chat, 'entity', tokens['entity'])
    envelope = drafts.prepare(chat)
    status = advisor.status()
    envelope['admission'] = {key: status[key] for key in ('session_id','game_version','snapshot_id','tick','captured_at','scene','fresh','live')}
    envelope['admission']['scope'] = 'recent_exporter_observation'
    request = dict(chat_id=chat, request_id=str(uuid4()), turn_id=str(uuid4()), game_session=state['session_id'],
                   text='Explain these observed people', attachment_ids=[item['attachment_id']])
    queue = TargetQueue(store);queue.initialize()
    yield queue, store, request, envelope, drafts
    store.close()


def enqueue(queue, request, envelope):
    return queue._enqueue_prepared(request, envelope, queue.clock())


def test_atomic_original_evidence_and_exact_replay_survive_restart(queued):
    queue, store, request, envelope, _ = queued
    ack = enqueue(queue, request, envelope)
    assert ack['accepted'] and ack['provider_dispatch'] == 'not_implemented'
    assert store.turns(request['chat_id'])[0]['status'] == 'queued'
    events = store.events(request['chat_id'])
    assert [e['kind'] for e in events] == ['user', 'target_evidence']
    assert {e['game_session'] for e in events} == {request['game_session']}
    assert events[1]['payload']['envelope'] == envelope
    assert ack == enqueue(queue, request, envelope) and len(store.events(request['chat_id'])) == 2
    # No migration/replay auto-dispatch: a fresh real store retains queued status.
    other = ChatStore(store.directory, recover=True)
    try:
        restored = TargetQueue(other)
        assert restored.initialize() is False
        assert restored.lookup(request) == ack
        changed = restored.accepted_evidence(request['request_id']);changed['attachments'][0]['rows'][0]['id'] = 999
        assert restored.accepted_evidence(request['request_id']) == envelope
        assert other.turns(request['chat_id'])[0]['status'] == 'queued'
    finally: other.close()


@pytest.mark.parametrize('change', ['text','chat_id','turn_id','game_session','attachment_ids'])
def test_same_request_cannot_change_its_intent(queued, change):
    queue, store, request, envelope, _ = queued
    ack = enqueue(queue, request, envelope);changed = deepcopy(request)
    changed[change] = 'Different question' if change == 'text' else [str(uuid4())] if change == 'attachment_ids' else str(uuid4())
    with pytest.raises(ValueError, match='different send'):
        queue.lookup(changed)
    assert queue.lookup(request) == ack and len(store.events(request['chat_id'])) == 2


@pytest.mark.parametrize('target', ['events','syx_target_queue'])
def test_failure_after_partial_inserts_rolls_back_turn_and_all_events(queued, target):
    queue, store, request, envelope, _ = queued
    condition = "WHEN NEW.kind='target_evidence'" if target == 'events' else ''
    store.db.execute(f"CREATE TRIGGER reject_accept BEFORE INSERT ON {target} {condition} BEGIN SELECT RAISE(ABORT,'injected_failure'); END")
    store.db.commit()
    with pytest.raises(ValueError, match='no partial turn'):
        enqueue(queue, request, envelope)
    assert store.turns(request['chat_id']) == [] and store.events(request['chat_id']) == []
    assert queue.lookup(request) is None


@pytest.mark.parametrize('change', ['runtime','hash','selection','stale','unknown','credential','text_secret','route','attachment','lease'])
def test_failed_admission_leaves_no_accepted_turn(queued, change):
    queue, store, request, envelope, _ = queued
    if change == 'runtime': envelope['admission']['session_id'] = str(uuid4())
    elif change == 'hash': envelope['attachments'][0]['rows'][0]['tile_x'] = 900
    elif change == 'selection': envelope['attachments'] = []
    elif change == 'stale': envelope['admission']['captured_at'] = (datetime.now(timezone.utc)-timedelta(seconds=31)).isoformat()
    elif change == 'unknown': envelope['admission']['live'] = False
    elif change == 'credential': envelope['attachments'][0]['rows'][0]['note'] = store.secrets[0]
    elif change == 'text_secret': request['text'] = store.secrets[0]
    elif change == 'route':
        store.db.execute("UPDATE chats SET model='deepseek-flash' WHERE chat_id=?", (request['chat_id'],));store.db.commit()
    elif change == 'attachment': store.attach(request['chat_id'], str(uuid4()))
    elif change == 'lease':
        with pytest.raises(ValueError, match='lease'):
            queue._enqueue_prepared(request,envelope,queue.clock()-3)
        assert store.turns(request['chat_id']) == []
        return
    before = store.events(request['chat_id'])
    with pytest.raises(ValueError): enqueue(queue, request, envelope)
    assert store.turns(request['chat_id']) == [] and store.events(request['chat_id']) == before


def test_busy_chat_cancel_and_new_explicit_request(queued):
    queue, store, request, envelope, _ = queued
    ack = enqueue(queue, request, envelope)
    next_request = dict(request, request_id=str(uuid4()), turn_id=str(uuid4()))
    with pytest.raises(ValueError, match='already has'):
        enqueue(queue, next_request, envelope)
    assert queue.cancel(request) is True and queue.cancel(request) is False
    assert store.turns(request['chat_id'])[0]['status'] == 'cancelled'
    assert queue.lookup(request) == ack  # original acceptance is not a new dispatch
    assert enqueue(queue, next_request, envelope)['turn_id'] == next_request['turn_id']
    assert len(store.turns(request['chat_id'])) == 2


def test_other_running_turn_and_duplicate_turn_refuse(queued):
    queue, store, request, envelope, _ = queued
    running = str(uuid4());store.begin(request['chat_id'], running, request['game_session'], 'Existing question')
    before = store.events(request['chat_id'])
    with pytest.raises(ValueError, match='already has'): enqueue(queue, request, envelope)
    assert store.events(request['chat_id']) == before
    store.finish(request['chat_id'], running, 'failed')
    request['turn_id'] = running
    with pytest.raises(ValueError, match='no partial turn'): enqueue(queue, request, envelope)
    assert store.events(request['chat_id']) == before


def test_extension_versions_receipts_cascade_and_evidence_integrity(queued):
    queue, store, request, envelope, _ = queued
    assert HistoryCandidate(store).initialize() is True
    assert store.db.execute('PRAGMA user_version').fetchone()[0] == 1
    enqueue(queue, request, envelope)
    assert HistoryCandidate(store).unread(request['chat_id']) == []
    store.db.execute("UPDATE syx_target_queue SET envelope='{}'");store.db.commit()
    with pytest.raises(ValueError, match='integrity'): queue.lookup(request)
    store.delete(request['chat_id'])
    assert store.db.execute('SELECT count(*) FROM syx_target_queue').fetchone()[0] == 0
    store.db.execute("UPDATE syx_ux_schema SET version=9 WHERE component='target_queue'");store.db.commit()
    with pytest.raises(ValueError, match='Unknown'): queue.initialize()


def test_receipts_first_and_nested_transaction_refusal(tmp_path):
    store = ChatStore(tmp_path/'receipt-first')
    try:
        HistoryCandidate(store).initialize();queue=TargetQueue(store)
        assert queue.initialize() is True
        store.db.execute('BEGIN')
        with pytest.raises(ValueError, match='own transaction'): queue.initialize()
        assert store.db.in_transaction
        store.db.rollback()
    finally: store.close()


def test_ack_only_clears_exact_accepted_targets_and_preserves_new_chips(queued):
    queue, store, request, envelope, drafts = queued
    ack = enqueue(queue, request, envelope)
    old = drafts.preview(request['chat_id'])[0]
    capture_id = old['capture']['capture_id']
    new = drafts.stage(request['chat_id'], 'entity', capture_id, offset=1)
    drafts.clear_accepted(request['chat_id'], ack['accepted_targets'])
    assert drafts.preview(request['chat_id']) == [new]
    drafts.clear_accepted(request['chat_id'], ack['accepted_targets'])
    assert drafts.preview(request['chat_id']) == [new]
    drafts.clear_accepted(str(uuid4()), ack['accepted_targets'])
    assert drafts.preview(request['chat_id']) == [new]


def test_changed_accepted_hash_refuses_whole_clear_batch(queued):
    queue, _, request, envelope, drafts = queued
    ack = enqueue(queue, request, envelope)
    forged = deepcopy(ack['accepted_targets']);forged[0]['observation_sha256'] = '0'*64
    before = drafts.preview(request['chat_id'])
    with pytest.raises(ValueError, match='nothing cleared'):
        drafts.clear_accepted(request['chat_id'], forged)
    assert drafts.preview(request['chat_id']) == before


from mcp import ClientSession
from mcp.client.stdio import stdio_client
from dev.chat_target_transport import McpTargetDrafts
from test_chat_target_transport import transport_state, parameters, create


def test_owned_mcp_acceptance_restart_lost_ack_and_new_chip_preservation(transport_state, tmp_path):
    path, state = transport_state
    async def run():
        store = ChatStore(tmp_path/'actual-mcp-queue')
        try:
            queue = TargetQueue(store);queue.initialize()
            cid = store.new(state['session_id'],model='deepseek-v4-pro')['chat_id']
            async with stdio_client(parameters(path)) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize();token = await create(session)
                    adapter = McpTargetDrafts(session);old = await adapter.stage(cid,'entity',token)
                    request = dict(chat_id=cid,request_id=str(uuid4()),turn_id=str(uuid4()),game_session=state['session_id'],
                                   text='Explain this captured person',attachment_ids=[old['attachment_id']])
                    admission = TargetAdmission(queue,adapter);ack = await admission.accept(**request)
                    assert adapter.preview(cid) == [old]  # acceptance does not clear before ack
                    newer = await adapter.stage(cid,'entity',token,offset=1)
                    other = ChatStore(store.directory,recover=True)
                    try:
                        restored = TargetAdmission(TargetQueue(other),adapter)
                        real = adapter.prepare
                        async def must_not_prepare(*a,**kw): raise AssertionError('Lost ack replay reread the game')
                        adapter.prepare = must_not_prepare
                        assert await restored.accept(**request) == ack
                        assert await restored.acknowledge(request) == ack
                        assert adapter.preview(cid) == [newer]
                        await restored.acknowledge(request)
                        assert adapter.preview(cid) == [newer]
                        adapter.prepare = real
                        # Subsequent explicit attach cannot change the accepted turn's original runtime.
                        other.attach(cid,str(uuid4()))
                        assert await restored.accept(**request) == ack
                        assert other.turns(cid)[0]['game_session'] == request['game_session']
                        export=json.loads(other.export(cid).read_text())
                        saved=next(e for e in export['events'] if e['kind']=='target_evidence')['payload']['envelope']
                        assert saved['attachments'][0]['capture']['tick']==old['capture']['tick']
                        assert saved['attachments'][0]['rows']==old['rows']
                    finally:other.close()
        finally:store.close()
    asyncio.run(run())


def test_exact_selection_and_empty_send_runtime_guard_over_stdio(transport_state,tmp_path):
    path,state=transport_state
    async def run():
        store=ChatStore(tmp_path/'guard-queue')
        try:
            queue=TargetQueue(store);queue.initialize()
            cid=store.new(state['session_id'],model='deepseek-v4-pro')['chat_id']
            async with stdio_client(parameters(path)) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize();adapter=McpTargetDrafts(session);admission=TargetAdmission(queue,adapter)
                    request=dict(chat_id=cid,request_id=str(uuid4()),turn_id=str(uuid4()),game_session=str(uuid4()),
                                 text='Plain question',attachment_ids=[])
                    with pytest.raises(ValueError,match='runtime or target'):await admission.accept(**request)
                    request['game_session']=state['session_id']
                    token=await create(session);item=await adapter.stage(cid,'entity',token)
                    with pytest.raises(ValueError,match='target selection'):await admission.accept(**request)
                    with pytest.raises(ValueError,match='No durable acceptance'):await admission.acknowledge(request)
                    assert adapter.preview(cid)==[item] and store.turns(cid)==[]
        finally:store.close()
    asyncio.run(run())


def test_cancel_before_prepare_returns_never_creates_a_partial_turn(transport_state,tmp_path):
    path,state=transport_state
    async def run():
        store=ChatStore(tmp_path/'cancel-queue')
        try:
            queue=TargetQueue(store);queue.initialize();cid=store.new(state['session_id'],model='deepseek-v4-pro')['chat_id']
            async with stdio_client(parameters(path)) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize();token=await create(session);adapter=McpTargetDrafts(session)
                    item=await adapter.stage(cid,'entity',token);entered=asyncio.Event()
                    async def blocked(*args,**kwargs):entered.set();await asyncio.Event().wait()
                    adapter.prepare=blocked
                    request=dict(chat_id=cid,request_id=str(uuid4()),turn_id=str(uuid4()),game_session=state['session_id'],
                                 text='Keep this draft',attachment_ids=[item['attachment_id']])
                    task=asyncio.create_task(TargetAdmission(queue,adapter).accept(**request))
                    await entered.wait();task.cancel()
                    with pytest.raises(asyncio.CancelledError):await task
                    assert adapter.preview(cid)==[item] and store.events(cid)==[] and store.turns(cid)==[]
        finally:store.close()
    asyncio.run(run())


def test_busy_database_is_a_refusal_without_target_loss(queued):
    queue,store,request,envelope,drafts=queued
    other=sqlite3.connect(store.directory/'history.sqlite3')
    try:
        other.execute('BEGIN IMMEDIATE');store.db.execute('PRAGMA busy_timeout=10')
        with pytest.raises(ValueError,match='no partial turn'):enqueue(queue,request,envelope)
        assert store.events(request['chat_id'])==[] and drafts.preview(request['chat_id'])
    finally:other.rollback();other.close()


def test_uncommitted_acceptance_cannot_be_acknowledged(queued):
    queue,store,request,envelope,_=queued
    enqueue(queue,request,envelope)
    store.db.execute('BEGIN')
    try:
        with pytest.raises(ValueError,match='committed'):queue.lookup(request)
        with pytest.raises(ValueError,match='committed'):queue.accepted_evidence(request['request_id'])
    finally:store.db.rollback()


def test_oversized_or_too_nested_evidence_never_begins_a_turn(queued):
    queue,store,request,envelope,_=queued
    oversized=dict(envelope,extra='x'*32768)
    with pytest.raises(ValueError,match='32 KiB'):enqueue(queue,request,oversized)
    nested=[]
    for _ in range(2000):nested=[nested]
    with pytest.raises(ValueError,match='nested'):enqueue(queue,request,dict(envelope,extra=nested))
    assert store.turns(request['chat_id'])==[] and queue.lookup(request) is None


def test_replay_resolves_before_expired_or_invalid_new_preparation(queued):
    queue,_,request,envelope,_=queued
    ack=enqueue(queue,request,envelope)
    assert queue._enqueue_prepared(request,{'invalid':'already accepted'},float('-inf'))==ack


@pytest.mark.parametrize('where',['envelope','item','admission','retention'])
def test_extra_unprovenance_fields_refuse_atomically(queued,where):
    queue,store,request,envelope,_=queued
    target={'envelope':envelope,'item':envelope['attachments'][0],
            'admission':envelope['admission'],'retention':envelope['attachments'][0]['retention_hint']}[where]
    target['unreviewed_extra']='not captured evidence'
    with pytest.raises(ValueError):enqueue(queue,request,envelope)
    assert store.events(request['chat_id'])==[] and queue.lookup(request) is None


def test_concurrent_exact_retry_resolves_acceptance_after_other_call_clears_targets(transport_state,tmp_path):
    path,state=transport_state
    async def run():
        store=ChatStore(tmp_path/'racing-queue')
        try:
            queue=TargetQueue(store);queue.initialize();cid=store.new(state['session_id'],model='deepseek-v4-pro')['chat_id']
            async with stdio_client(parameters(path)) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize();token=await create(session);adapter=McpTargetDrafts(session)
                    old=await adapter.stage(cid,'entity',token);admission=TargetAdmission(queue,adapter)
                    request=dict(chat_id=cid,request_id=str(uuid4()),turn_id=str(uuid4()),game_session=state['session_id'],
                                 text='Send once',attachment_ids=[old['attachment_id']])
                    real=adapter.prepare;entered=asyncio.Event();release=asyncio.Event();calls=0
                    async def delayed(*args,**kwargs):
                        nonlocal calls
                        calls+=1
                        if calls==1:entered.set();await release.wait()
                        return await real(*args,**kwargs)
                    adapter.prepare=delayed
                    first=asyncio.create_task(admission.accept(**request));await entered.wait()
                    ack=await admission.accept(**request);await admission.acknowledge(request)
                    newer=await adapter.stage(cid,'entity',token,offset=1)
                    release.set()
                    assert await first==ack
                    assert len(store.turns(cid))==1 and len(store.events(cid))==2
                    assert adapter.preview(cid)==[newer]
        finally:store.close()
    asyncio.run(run())


@pytest.mark.parametrize('bundle',['latest-user-test.zip','previous-user-test.zip'])
def test_actual_bundled_store_extension_compatibility_and_delete(queued,tmp_path,bundle):
    import importlib.util
    import zipfile
    _,_,request,envelope,_=queued
    with zipfile.ZipFile(Path(__file__).parent/'releases'/bundle) as archive:
        code=archive.read('syx_chat_store.py')
    module_path=tmp_path/'bundled_store.py';module_path.write_bytes(code)
    spec=importlib.util.spec_from_file_location('actual_bundled_target_store',module_path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    history=tmp_path/'bundled-history';legacy=module.ChatStore(history)
    try:
        cid=legacy.new(request['game_session'],model='deepseek-v4-pro')['chat_id']
        legacy_queue=TargetQueue(legacy);legacy_queue.initialize()
        bound_request=dict(request,chat_id=cid);bound_envelope=dict(envelope,chat_id=cid)
        ack=enqueue(legacy_queue,bound_request,bound_envelope)
        assert legacy.turns(cid)[0]['status']=='queued'
    finally:legacy.close()
    modern=ChatStore(history,recover=True)
    try:
        restored=TargetQueue(modern)
        assert restored.initialize() is False and restored.lookup(bound_request)==ack
        assert restored.accepted_evidence(bound_request['request_id'])==bound_envelope
        modern.delete(cid)
        assert modern.db.execute('SELECT count(*) FROM syx_target_queue').fetchone()[0]==0
        assert modern.db.execute('PRAGMA foreign_key_check').fetchall()==[]
    finally:modern.close()
