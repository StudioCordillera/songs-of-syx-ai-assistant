from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
import json
import threading
import time
from uuid import uuid4
import pytest
from pydantic import ValidationError
from syx_stockpiles import StockpileSelection, query_stockpiles, validate_page
from test_syx_live import live

SPEC={'room_ids':[17],'resource_ids':['grain'],'fields':['stored_raw']}


def page():
    return {'read_mode':'stockpile_page','observer_phase':'GAME.addAfterUpdate','scope':'instantiated_city_stockpile_bookkeeping',
        'coverage':'partial','tick':7,'scene':{'active_view':'city'},'ui_context':{'active_view':'city'},'consistency':'one callback',
        'data':{'rows':[{'matrix_position':0,'room_id':17,'resource_id':'grain','room_blueprint_id':'warehouse',
            'anchor_tile_x':8,'anchor_tile_y':9,'room_active':True,'stored_raw':0}],
            'scanned_cells':1,'cell_errors':0,'next_cursor':None,'cursor_kind':'stockpile_room_resource_matrix',
            'room_source_kind':'explicit_room_ids','room_ids':[17],'resource_ids':['grain'],'room_count_total':1,
            'resource_registry_count':42,'resource_scan_limit':1000,'stockpile_blueprint_id':'warehouse'}}


@pytest.mark.parametrize('change',[
    {'resource_ids':[]},{'resource_ids':['grain','grain']},{'room_ids':[True]},{'room_ids':[-1]},
    {'room_ids':[1,1]},{'room_ids':list(range(101))},{'fields':[]},{'fields':['private']},
    {'fields':['stored_raw','stored_raw']},{'active':'true'},{'limit':True},{'limit':101},
    {'scan_limit':4097},{'cursor':2},{'expected_session_id':'1-1-1-1-1'},
    {'filters':[{'field':'stored_raw','op':'refresh','value':1}]},
    {'filters':[{'field':'stored_raw','op':'eq','value':True}]},
    {'filters':[{'field':'stored_raw','op':'eq','value':2**31}]},
    {'filters':[{'field':'stored_raw','op':'eq','value':0}]*5},
    {'resource_ids':['😀'*51]},{'resource_ids':['\ud800']},{'method':'deposit'}])
def test_invalid_stockpile_selection_never_writes_request(live, change):
    with pytest.raises(ValidationError):query_stockpiles(live[0],{**SPEC,**change})
    assert not (live[0].snapshot_path.parent/'stockpile-request.txt').exists()


def test_stockpile_wire_preserves_unicode_key_without_framing_injection():
    key='粮\nlimit=100 😀'
    selection=StockpileSelection(resource_ids=[key],filters=[{'field':'stored_raw','op':'gte','value':-(2**31)}],active=False)
    wire=selection.wire(str(uuid4()),str(uuid4()),int(time.time()*1000+8000))
    assert wire.count('\n')==12 and 'limit=100' not in wire and 'active=false\n' in wire
    assert 'filters=stored_raw:gte:-2147483648\n' in wire
    StockpileSelection(resource_ids=['😀'*50])
    wide=StockpileSelection(resource_ids=['a'*98+str(i) for i in range(100)])
    with pytest.raises(ValueError,match='8 KiB'):wide.wire(str(uuid4()),str(uuid4()),int(time.time()*1000+8000))
    with pytest.raises(ValueError,match='UUID'):selection.wire('bad',str(uuid4()),int(time.time()*1000+8000))


def responder(directory,stop,transform):
    seen=set()
    while not stop.is_set():
        try:
            parts=dict(line.split('=',1) for line in (directory/'stockpile-request.txt').read_text().splitlines())
            if parts['request_id'] not in seen:
                seen.add(parts['request_id'])
                result={**page(),'request_id':parts['request_id'],'session_id':parts['session'],'game_version':'0.71.44',
                    'available':True,'captured_at':datetime.now(timezone.utc).isoformat()}
                temp=directory/'stockpile-test.tmp';temp.write_text(json.dumps(transform(result)));temp.replace(directory/'stockpile-response.json')
        except FileNotFoundError:pass
        time.sleep(.005)


def response(advisor,transform=lambda r:r,spec=SPEC):
    stop=threading.Event()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(responder,advisor.snapshot_path.parent,stop,transform)
        try:return query_stockpiles(advisor,spec,timeout=1)
        finally:stop.set();future.result(timeout=1)


def test_stockpile_transport_does_not_depend_on_cached_rooms_and_preserves_zero(live):
    advisor,state=live;state['domains']['resources']['data']={};advisor.snapshot_path.write_text(json.dumps(state))
    result=response(advisor)
    assert result['data']['rows'][0]['stored_raw']==0
    assert not (advisor.snapshot_path.parent/'regional-request.txt').exists()
    assert not (advisor.snapshot_path.parent/'entity-request.txt').exists()
    state['demo']=True;advisor.snapshot_path.write_text(json.dumps(state))
    with pytest.raises(ValueError,match='non-demo'):query_stockpiles(advisor,SPEC)


@pytest.mark.parametrize('path,value',[
    (('scope',),'city'),(('observer_phase',),'worker'),(('tick',),True),(('scene',),None),
    (('data','room_source_kind'),'current_warehouse_instance_slots'),(('data','room_ids'),[True]),
    (('data','resource_ids'),['wood']),(('data','room_count_total'),2),(('data','resource_registry_count'),1001),
    (('data','cell_errors'),True),(('data','cell_errors'),1),(('data','next_cursor'),0),
    (('data','rows',0,'room_id'),True),(('data','rows',0,'room_id'),18),
    (('data','rows',0,'resource_id'),'wood'),(('data','rows',0,'room_blueprint_id'),'other'),
    (('data','rows',0,'matrix_position'),1),(('data','rows',0,'anchor_tile_x'),-1),
    (('data','rows',0,'room_active'),1),(('data','rows',0,'stored_raw'),None),
    (('data','rows',0,'stored_raw'),2**31),(('data','rows',0,'private'),0)])
def test_stockpile_response_rejects_identity_projection_and_bound_corruption(live,path,value):
    def transform(r):
        at=r
        for key in path[:-1]:at=at[key]
        at[path[-1]]=value;return r
    with pytest.raises(ValueError):response(live[0],transform)


def test_stockpile_filtered_empty_page_is_not_end_and_negative_raw_is_not_zero():
    r=page();d=r['data'];d.update(rows=[],scanned_cells=1,next_cursor=1,room_ids=[],room_source_kind='current_warehouse_instance_slots',room_count_total=3)
    selection=StockpileSelection(resource_ids=['grain'],scan_limit=1,filters=[{'field':'stored_raw','op':'gt','value':5}])
    assert validate_page(r,selection)['data']['next_cursor']==1
    r=page();r['data']['rows'][0]['stored_raw']=-(2**31)
    assert validate_page(r,StockpileSelection(**SPEC))['data']['rows'][0]['stored_raw']==-(2**31)
    r['data']['rows'][0]['stored_raw']=True
    with pytest.raises(ValueError):validate_page(r,StockpileSelection(**SPEC))


def test_stockpile_response_checks_predicates_missing_cells_early_stop_and_byte_bound():
    r=page();selection=StockpileSelection(**SPEC,active=False)
    with pytest.raises(ValueError,match='active'):validate_page(r,selection)
    selection=StockpileSelection(**SPEC,filters=[{'field':'stored_raw','op':'gt','value':0}])
    with pytest.raises(ValueError,match='counter predicate'):validate_page(r,selection)
    r=page();r['data']['rows']=[]
    with pytest.raises(ValueError,match='Missing unfiltered'):validate_page(r,StockpileSelection(**SPEC))
    r=page();r['data'].update(room_ids=[],room_source_kind='current_warehouse_instance_slots',room_count_total=3,next_cursor=1)
    with pytest.raises(ValueError,match='early stop'):validate_page(r,StockpileSelection(resource_ids=['grain'],fields=['stored_raw']))
    r=page();r['ui_context']['text']='x'*70000
    with pytest.raises(ValueError,match='64 KiB'):validate_page(r,StockpileSelection(**SPEC))


def test_stockpile_response_rejects_changed_anchor_within_one_room_slot():
    r=page();d=r['data'];second=deepcopy(d['rows'][0]);second.update(matrix_position=1,resource_id='wood',anchor_tile_x=99)
    d.update(rows=d['rows']+[second],resource_ids=['grain','wood'],scanned_cells=2)
    selection=StockpileSelection(room_ids=[17],resource_ids=['grain','wood'],fields=['stored_raw'])
    with pytest.raises(ValueError,match='slot identity'):validate_page(r,selection)


def test_stockpile_requests_use_shared_transport_lock_and_fresh_session(live):
    advisor,_=live;stop=threading.Event()
    with ThreadPoolExecutor(max_workers=3) as pool:
        worker=pool.submit(responder,advisor.snapshot_path.parent,stop,lambda r:r)
        try:
            reads=[pool.submit(query_stockpiles,advisor,SPEC,timeout=2) for _ in range(2)]
            results=[f.result(timeout=3) for f in reads]
            assert results[0]['request_id']!=results[1]['request_id']
            with pytest.raises(ValueError,match='Session changed'):
                query_stockpiles(advisor,{**SPEC,'expected_session_id':str(uuid4())})
        finally:stop.set();worker.result(timeout=1)


def test_stockpile_python_and_game_projection_predicate_allowlists_agree():
    import re
    from pathlib import Path
    from syx_stockpiles import CounterFilter
    text=(Path(__file__).parent/'mod/src/main/java/syx/assistant/StockpileReadRequest.java').read_text()
    def names(name):
        return set(re.findall(r'"([a-z_]+)"',re.search(rf'{name}=Set.of\(([^;]+)\);',text)[1]))
    selection=StockpileSelection.model_json_schema()
    predicates=CounterFilter.model_json_schema()
    assert names('FIELDS')==set(selection['properties']['fields']['items']['enum'])
    assert names('COUNTERS')==set(predicates['properties']['field']['enum'])
    assert names('OPS')==set(predicates['properties']['op']['enum'])
