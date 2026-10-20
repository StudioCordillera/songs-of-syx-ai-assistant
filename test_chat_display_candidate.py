"""Disposable protocol/SQLite tests; no normal histories, providers or native input."""
import base64
import json
from uuid import uuid4
import pytest
from dev.chat_display_candidate import DisplayBroker,receipt
from syx_chat_store import ChatStore


def uid():return str(uuid4())


def completed(store,chat,text='Answer',*,status='completed',final=True):
    tid=uid();cid=chat['chat_id'];session=chat['attached_session']
    store.begin(cid,tid,session,'Question')
    store.append(cid,tid,session,'assistant',dict(text=text,completed=final))
    eid=store.events(cid)[-1]['event_id']
    if status=='interrupted':
        restarted=ChatStore(store.directory,recover=True);restarted.close()
    elif status!='running':store.finish(cid,tid,status)
    return tid,eid


def fields(raw):
    values={}
    for line in raw.decode('ascii').splitlines():
        key,_,value=line.partition('=');values.setdefault(key,[]).append(value)
    return values


@pytest.fixture
def fixture(tmp_path):
    store=ChatStore(tmp_path);clock=[100.]
    chat=store.new(uid(),model='deepseek-v4-pro')
    broker=DisplayBroker(store,clock=lambda:clock[0]);broker.history.initialize()
    yield store,chat,broker,clock
    store.close()


def presence(chat):return dict(session_id=chat['attached_session'],fresh=True,live=True)


def ack(broker,frame,chat,eids):
    return broker.acknowledge(receipt(frame,eids,chat['attached_session']),presence=presence(chat))


def test_frame_stable_until_changed_and_publish_never_marks_read(fixture):
    store,c,b,clock=fixture;_,eid=completed(store,c)
    raw=b.publish(c['chat_id'],c['attached_session']);data=fields(raw)
    assert data['unread_total']==['1'] and len(data['reply'])==1
    clock[0]+=1
    assert b.publish(c['chat_id'],c['attached_session'])==raw
    assert len(b.history.unread(c['chat_id']))==1
    result=ack(b,raw,c,[eid,eid]);assert result['newly_read']==1
    assert ack(b,raw,c,[eid])['newly_read']==0
    after=fields(b.publish(c['chat_id'],c['attached_session']))
    assert after['frame']!=data['frame'] and after['unread_total']==['0'] and 'reply' not in after


def test_pending_final_needs_completed_turn_and_new_display_frame(fixture):
    store,c,b,_=fixture;tid,eid=completed(store,c,status='running')
    old=b.publish(c['chat_id'],c['attached_session'])
    assert fields(old)['unread_total']==['0'] and 'reply' not in fields(old)
    store.finish(c['chat_id'],tid,'completed')
    with pytest.raises(ValueError,match='not issued'):ack(b,old,c,[eid])
    new=b.publish(c['chat_id'],c['attached_session'])
    assert fields(new)['unread_total']==['1'] and new!=old
    assert ack(b,new,c,[eid])['newly_read']==1


@pytest.mark.parametrize('status,final,text',[('failed',True,'Partial'),('cancelled',True,'Partial'),('interrupted',True,'Partial'),('completed',False,'Partial'),('completed',True,'  ')])
def test_failed_empty_and_partial_replies_not_counted_or_eligible(fixture,status,final,text):
    store,c,b,_=fixture;_,eid=completed(store,c,text,status=status,final=final)
    raw=b.publish(c['chat_id'],c['attached_session'])
    assert fields(raw)['unread_total']==['0'] and 'reply' not in fields(raw)
    with pytest.raises(ValueError,match='not issued'):ack(b,raw,c,[eid])


def test_ack_of_earlier_selected_frame_keeps_other_chat_and_newer_reply_unread(fixture):
    store,a,b,_=fixture;c=store.new(a['attached_session'],model='deepseek-v4-pro')
    _,ae=completed(store,a);old=b.publish(a['chat_id'],a['attached_session'])
    _,be=completed(store,c);_,new=completed(store,a)
    b.publish(c['chat_id'],c['attached_session'])
    with pytest.raises(ValueError,match='not issued'):ack(b,old,a,[ae,new])
    assert len(b.history.unread(a['chat_id']))==2
    assert ack(b,old,a,[ae])['newly_read']==1
    assert [r['event_id'] for r in b.history.unread(a['chat_id'])]==[new]
    assert [r['event_id'] for r in b.history.unread(c['chat_id'])]==[be]


@pytest.mark.parametrize('change',['epoch','frame','chat','runtime','observed_session','missing','duplicate_scalar','protocol','overlong','bad_ascii','empty_events','too_many_events'])
def test_forged_or_malformed_receipt_never_clears_unread(fixture,change):
    store,c,b,_=fixture;_,eid=completed(store,c);raw=b.publish(c['chat_id'],c['attached_session'])
    wire=receipt(raw,[eid],c['attached_session'])
    if change in {'epoch','frame','chat','runtime','observed_session'}:
        lines=wire.decode().splitlines();wire=('\n'.join(change+'='+uid() if line.startswith(change+'=') else line for line in lines)+'\n').encode()
    elif change=='missing':wire=b'\n'.join(line for line in wire.split(b'\n') if not line.startswith(b'frame='))
    elif change=='duplicate_scalar':wire+=b'protocol=3\n'
    elif change=='protocol':wire=wire.replace(b'protocol=3',b'protocol=2')
    elif change=='overlong':wire+=b'x'*16384
    elif change=='bad_ascii':wire+=b'\xff'
    elif change=='empty_events':wire=b'\n'.join(line for line in wire.split(b'\n') if not line.startswith(b'event='))
    elif change=='too_many_events':wire+=('event='+eid+'\n').encode()*100
    with pytest.raises(ValueError):b.acknowledge(wire,presence=presence(c))
    assert len(b.history.unread(c['chat_id']))==1


@pytest.mark.parametrize('status',[dict(fresh=False,live=True),dict(fresh=True,live=False),dict(fresh=1,live=True),dict(fresh=True,live=1),dict(fresh=True,live=True,session_id='wrong')])
def test_receipt_needs_fresh_matching_real_presence_from_caller(fixture,status):
    store,c,b,_=fixture;_,eid=completed(store,c);raw=b.publish(c['chat_id'],c['attached_session'])
    state={**presence(c),**status}
    with pytest.raises(ValueError,match='presence'):b.acknowledge(receipt(raw,[eid],c['attached_session']),presence=state)
    assert len(b.history.unread(c['chat_id']))==1


def test_expiry_restart_and_eviction_refuse_old_frames(fixture):
    store,c,b,clock=fixture;_,eid=completed(store,c);old=b.publish(c['chat_id'],c['attached_session'])
    restarted=DisplayBroker(store,clock=lambda:clock[0])
    with pytest.raises(ValueError,match='restarted'):ack(restarted,old,c,[eid])
    clock[0]+=b.TTL
    with pytest.raises(ValueError,match='Expired'):ack(b,old,c,[eid])
    current=b.publish(c['chat_id'],c['attached_session'])
    assert fields(current)['frame']!=fields(old)['frame']
    for i in range(b.FRAME_CAP):
        other=store.new(c['attached_session'],title=str(i),model='deepseek-v4-pro');b.publish(other['chat_id'],c['attached_session'])
    assert len(b.frames)==b.FRAME_CAP
    with pytest.raises(ValueError,match='Expired'):ack(b,current,c,[eid])
    assert len(b.history.unread(c['chat_id']))==1


def test_changed_payload_refuses_whole_batch_without_receipts(fixture):
    store,c,b,_=fixture;_,one=completed(store,c);_,two=completed(store,c)
    raw=b.publish(c['chat_id'],c['attached_session'])
    with store.db:store.db.execute('UPDATE events SET payload=? WHERE event_id=?',(json.dumps(dict(text='Changed after issue',completed=True)),two))
    with pytest.raises(ValueError,match='payload changed'):ack(b,raw,c,[one,two])
    assert len(b.history.unread(c['chat_id']))==2


def test_old_runtime_messages_keep_original_session_and_current_runtime(fixture):
    store,c,b,_=fixture;_,old_event=completed(store,c)
    old_session=c['attached_session'];runtime=uid();store.attach(c['chat_id'],runtime,explicit=False)
    current=store.chat(c['chat_id']);_,new_event=completed(store,current)
    raw=b.publish(c['chat_id'],runtime);data=fields(raw)
    assert data['runtime']==[runtime] and len(data['reply'])==2
    texts=[base64.b64decode(s).decode() for s in data['line']]
    assert 'Earlier game · Assistant: Answer' in texts
    with pytest.raises(ValueError,match='not issued'):
        b.acknowledge(receipt(raw,[old_event,new_event],runtime),presence=presence(current))
    assert b.acknowledge(receipt(raw,[old_event],old_session),presence=presence(current))['newly_read']==1
    assert len(b.history.unread(c['chat_id']))==1


def test_preview_omission_never_authenticates_hidden_event(fixture):
    store,c,b,_=fixture;b.WIRE_CAP=1400
    events=[completed(store,c,str(i)*300)[1] for i in range(3)]
    raw=b.publish(c['chat_id'],c['attached_session']);data=fields(raw)
    assert len(raw)<=1400 and data['omitted']==['true'] and data['unread_total']==['3']
    issued=[row.split('|')[1] for row in data.get('reply',[])]
    assert issued and len(issued)<3 and events[0] not in issued
    assert all(int(row.split('|')[0])<len(data['line']) for row in data['reply'])
    with pytest.raises(ValueError,match='not issued'):ack(b,raw,c,[events[0]])
    assert ack(b,raw,c,[issued[-1]])['newly_read']==1


def test_pro_filter_precedes_scan_budget_and_global_total_precedes_chat_cap(fixture):
    store,c,b,_=fixture;flash=store.new(c['attached_session'])
    for i in range(4):completed(store,flash,'Ignored')
    completed(store,c);b.history.ROW_CAP=3
    assert fields(b.publish(c['chat_id'],c['attached_session']))['unread_total']==['1']
    b.history.ROW_CAP=10000
    for i in range(102):completed(store,store.new(c['attached_session'],model='deepseek-v4-pro'))
    data=fields(b.publish(c['chat_id'],c['attached_session']))
    assert data['unread_total']==['103'] and data['unread_chat_count']==['103']
    assert data['chat_counts_complete']==['false'] and len(data['chat_unread'])==100
    assert any(row.startswith(c['chat_id']+'|') for row in data['chat_unread'])


def test_budget_refusal_is_unknown_not_zero_and_cannot_issue_receipts(fixture):
    store,c,b,_=fixture
    for i in range(3):completed(store,c)
    b.history.ROW_CAP=2
    with pytest.raises(ValueError,match='scan budget'):b.publish(c['chat_id'],c['attached_session'])
    raw=b.unavailable(c['attached_session']);data=fields(raw)
    assert data['counts']==['unavailable'] and 'unread_total' not in data and 'reply' not in data and 'chat_unread' not in data


def test_no_selected_runtime_frame_cannot_generate_receipt(fixture):
    store,c,b,_=fixture;completed(store,c)
    raw=b.publish(None,None);data=fields(raw)
    assert data['unread_total']==['1'] and 'runtime' not in data and 'chat' not in data
    with pytest.raises(ValueError,match='Selected'):receipt(raw,[],c['attached_session'])


def test_unchanged_refresh_uses_cache_but_own_and_external_commits_refresh_it(fixture):
    store,c,b,_=fixture;tid,eid=completed(store,c,status='running')
    first=b.publish(c['chat_id'],c['attached_session']);traces=[]
    store.db.set_trace_callback(traces.append)
    assert b.publish(c['chat_id'],c['attached_session'])==first
    assert not any('FROM events' in sql for sql in traces)
    traces.clear();store.finish(c['chat_id'],tid,'completed')
    assert fields(b.publish(c['chat_id'],c['attached_session']))['unread_total']==['1']
    assert any('FROM events' in sql for sql in traces)
    external=ChatStore(store.directory)
    try:completed(external,c)
    finally:external.close()
    traces.clear()
    assert fields(b.publish(c['chat_id'],c['attached_session']))['unread_total']==['2']
    assert any('FROM events' in sql for sql in traces)
    store.db.set_trace_callback(None)


def test_receipt_write_failure_rolls_back_every_insert(fixture):
    store,c,b,_=fixture;_,one=completed(store,c);_,two=completed(store,c)
    raw=b.publish(c['chat_id'],c['attached_session'])
    bad=max(one,two)
    # Disposable trigger injects failure inside the write transaction, not production schema.
    with store.db:store.db.execute("CREATE TRIGGER fail_receipt BEFORE INSERT ON syx_ux_reads WHEN NEW.event_id='"+bad+"' BEGIN SELECT RAISE(ABORT,'injected receipt write failure'); END")
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError,match='injected'):ack(b,raw,c,[one,two])
    assert len(b.history.unread(c['chat_id']))==2 and store.db.execute('SELECT count(*) FROM syx_ux_reads').fetchone()[0]==0
    with store.db:store.db.execute('DROP TRIGGER fail_receipt')
    assert ack(b,raw,c,[one,two])['newly_read']==2


@pytest.mark.parametrize('wire',[b'protocol=3\r\n',b'protocol=3',b'protocol=3\vframe=x\n'])
def test_noncanonical_receipt_line_framing_rejected(wire):
    with pytest.raises(ValueError,match='LF'):DisplayBroker.parse_receipt(wire)
