from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
import threading
import time
from uuid import uuid4

import pytest
from pydantic import ValidationError

from syx_live import EntitySelection,query_entities
from syx_mcp import Advisor

ROOT=Path(__file__).parent

@pytest.mark.parametrize('spec',[
    {'workplace_room_id':True},{'workplace_room_id':-1},{'workplace_room_id':2**31},
    {'workplace_room_id':'1'},{'workplace_room_id':1.5},{'fields':['privateAI']},{'method':'kill'},{'limit':True},{'cursor':-1},
    {'scan_limit':10001},{'entity_ids':[1,1]},{'fields':['stats'],'stat_ids':[]},
    {'fields':['stats'],'stat_ids':[1,2],'limit':51},{'tile_bounds':[0,0,0,2]},
    {'stat_filters':[{'stat_id':1,'op':'invoke','value':0}]},{'stat_ids':[1]},
])
def test_invalid_selections_are_rejected(spec):
    with pytest.raises(ValidationError):EntitySelection.model_validate(spec)

def test_wire_preserves_unicode_without_line_injection():
    spec=EntitySelection(race_id='race\nclass=anything 😀',fields=['id','stats'],stat_ids=[1],limit=2)
    wire=spec.wire(str(uuid4()),str(uuid4()),int(time.time()*1000+8000))
    assert wire.count('\n')==15 and 'anything' not in wire
    assert 'fields=id,stats\n' in wire

@pytest.fixture
def live(tmp_path):
    state=json.loads((ROOT/'snapshot.example.json').read_text())
    state.update(game_version='0.71.44',demo=False,game_loaded=True,session_id=str(uuid4()),captured_at=datetime.now(timezone.utc).isoformat())
    snapshot=tmp_path/'snapshot.json';snapshot.write_text(json.dumps(state))
    return Advisor(snapshot,tmp_path/'corpus.json'),state

def test_no_demo_or_stale_dispatch(live):
    advisor,state=live
    for change in ({'demo':True},{'demo':False,'captured_at':(datetime.now(timezone.utc)-timedelta(minutes=2)).isoformat()}):
        state.update(change);advisor.snapshot_path.write_text(json.dumps(state))
        with pytest.raises(ValueError,match='non-demo'):query_entities(advisor,{})
        assert not (advisor.snapshot_path.parent/'entity-request.txt').exists()

def respond(directory,stop,transform=lambda x:x):
    seen=set()
    while not stop.is_set():
        try:
            wire=(directory/'entity-request.txt').read_text()
            parts=dict(line.split('=',1) for line in wire.splitlines())
            if parts['request_id'] in seen:time.sleep(.005);continue
            seen.add(parts['request_id'])
            result={'request_id':parts['request_id'],'session_id':parts['session'],'game_version':'0.71.44',
                'captured_at':datetime.now(timezone.utc).isoformat(),'available':True,
                'data':{'rows':[{'id':7}],'scanned_slots':1,'next_cursor':None}}
            result=transform(result)
            tmp=directory/'response.tmp';tmp.write_text(json.dumps(result));tmp.replace(directory/'entity-response.json')
        except FileNotFoundError:pass
        time.sleep(.005)

def test_concurrent_clients_serialize_and_reject_session_mismatch(live):
    advisor,state=live;stop=threading.Event()
    # Separate Advisor objects simulate independent MCP clients sharing one directory.
    other=Advisor(advisor.snapshot_path,advisor.corpus_path)
    with ThreadPoolExecutor(max_workers=3) as pool:
        worker=pool.submit(respond,advisor.snapshot_path.parent,stop)
        try:
            reads=[pool.submit(query_entities,a,{'limit':1},timeout=2) for a in (advisor,other)]
            results=[f.result(timeout=3) for f in reads]
            assert results[0]['request_id']!=results[1]['request_id']
            assert all(r['data']['rows']==[{'id':7}] for r in results)
            with pytest.raises(ValueError,match='Session changed'):
                query_entities(advisor,{'expected_session_id':str(uuid4())})
        finally:stop.set();worker.result(timeout=1)

@pytest.mark.parametrize('change,match',[
    ({'session_id':'wrong'},'different session'),({'available':False,'reason':'No scene'},'No scene'),
    ({'data':{'rows':[{}]*101,'scanned_slots':1}},'bounded entity'),
    ({'captured_at':(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat()},'not recent')])
def test_response_identity_freshness_and_bounds(live,change,match):
    advisor,_=live;stop=threading.Event()
    with ThreadPoolExecutor(max_workers=1) as pool:
        worker=pool.submit(respond,advisor.snapshot_path.parent,stop,lambda r:{**r,**change})
        try:
            with pytest.raises(ValueError,match=match):query_entities(advisor,{},timeout=1)
        finally:stop.set();worker.result(timeout=1)

def test_missing_update_times_out_and_lock_is_reusable(live):
    advisor,_=live
    with pytest.raises(ValueError,match='did not answer'):query_entities(advisor,{},timeout=.6)
    # A second attempt can acquire the released transport lock; no stale lease remains.
    with pytest.raises(ValueError,match='did not answer'):query_entities(advisor,{},timeout=.6)


def test_workplace_filter_wire_is_optional_and_shared_by_capture():
    from syx_live import EntityCaptureSelection
    request,session=str(uuid4()),str(uuid4())
    expires=int(time.time()*1000+8000)
    legacy=EntitySelection(fields=['id']).wire(request,session,expires)
    assert 'workplace_room_id' not in legacy and len(legacy.splitlines())==15
    for mode in [EntitySelection,EntityCaptureSelection]:
        selection=mode(workplace_room_id=0,fields=['id'])
        wire=selection.wire(request,session,expires)
        assert wire.count('workplace_room_id=0\n')==1 and len(wire.splitlines())==16
