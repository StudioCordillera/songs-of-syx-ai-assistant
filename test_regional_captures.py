"""Regional capture protocol, complete-selection refusal and immutable paging boundaries."""
from datetime import datetime,timezone,timedelta
import json
from uuid import uuid4
import pytest
from pydantic import ValidationError
from syx_regions import RegionalCaptureSelection
from syx_capture import RegionalCaptures,TileCaptures,EntityCaptures
from test_syx_live import live
from test_syx_regions import response


@pytest.mark.parametrize('extra',[
 {'cursor':1},{'max_rows':2001},{'max_rows':True},{'limit':10},{'scan_limit':10001},
 {'scan_limit':1,'resource_ids':['a','b']},{'region_ids':list(range(101))},
 {'region_ids':[False]},{'fields':['private']},{'method':'ship'},
])
def test_invalid_capture_cannot_widen_public_boundary(extra):
    with pytest.raises(ValidationError):RegionalCaptureSelection.model_validate({'region_ids':[0],'resource_ids':['a'],**extra})


def test_capture_wire_and_large_raw_response_are_distinct_from_live_page(live):
    selection=RegionalCaptureSelection(region_ids=[17],resource_ids=['grain'],max_rows=2000)
    wire=selection.wire(str(uuid4()),str(uuid4()),1234567890123)
    assert 'protocol=2\n' in wire and 'limit=2000\n' in wire and 'scan_limit=10000\n' in wire
    def wide(result):
        result['ui_context']['text']='x'*100000
        return result
    assert len(response(live[0],wide,capture=True)['ui_context']['text'])==100000
    with pytest.raises(ValueError):response(live[0],wide,capture=False)


@pytest.mark.parametrize('tamper',[
 lambda r:{**r,'read_mode':'regional_page'},
 lambda r:{**r,'data':{**r['data'],'next_cursor':1}},
 lambda r:{**r,'data':{**r['data'],'cell_errors':1}},
 lambda r:{**r,'data':{**r['data'],'cell_errors':False}},
 lambda r:{**r,'data':{**r['data'],'rows':[]}},
 lambda r:{**r,'data':{**r['data'],'scanned_cells':0}},
 lambda r:{**r,'data':{**r['data'],'rows':r['data']['rows']*2}},
 lambda r:{**r,'data':{**r['data'],'rows':[{**r['data']['rows'][0],'region_id':18}]}},
 lambda r:{**r,'ui_context':{'text':'x'*(2*1024*1024)}},
])
def test_capture_transport_rejects_partial_wrong_mode_or_oversized_responses(live,tamper):
    with pytest.raises(ValueError):response(live[0],tamper,capture=True)


@pytest.fixture
def regional(live,monkeypatch):
    advisor,state=live
    ids=list(range(31));keys=[f'r{i}' for i in range(7)]
    rows=[{'region_id':rid,'resource_id':key,'accrued_output_raw':rid*7+i,'days_until_configured_output':0}
          for rid in ids for i,key in enumerate(keys)]
    payload={'request_id':str(uuid4()),'session_id':state['session_id'],'game_version':state['game_version'],
        'captured_at':state['captured_at'],'tick':12,'observer_phase':'GAME.addAfterUpdate','read_mode':'regional_capture',
        'scope':'campaign_world_regions','coverage':'partial','scene':{'active_view':'settlement'},
        'ui_context':{'active_view':'settlement'},'consistency':'one native callback',
        'data':{'rows':rows,'scanned_cells':len(rows),'cell_errors':0,'next_cursor':None,
            'region_ids':ids,'resource_ids':keys,'scanned_regions':203,'scanned_resources':42,
            'region_scan_limit':1023,'resource_scan_limit':1000,'cursor_kind':'requested_region_resource_matrix'}}
    calls=[]
    def read(*args,**kwargs):
        calls.append((args,kwargs));return json.loads(json.dumps(payload))
    monkeypatch.setattr('syx_regions._read_entities',read)
    return RegionalCaptures(advisor),advisor,state,payload,calls,{'region_ids':ids,'resource_ids':keys}


def test_pages_are_immutable_and_keep_original_context_after_live_state_changes(regional):
    store,advisor,state,payload,calls,spec=regional
    meta=store.create(spec)['capture'];token=meta['capture_id']
    assert meta['row_count']==217 and meta['scanned_cells']==217 and meta['selection_complete']
    assert meta['capture_kind']=='regional_output' and calls[0][1]['capture'] is True
    page=store.read(token,limit=100,include_ui_context=True);page['rows'][0]['accrued_output_raw']=999
    payload['data']['rows'][0]['accrued_output_raw']=998
    state.update(tick=900,scene={'active_view':'world'});advisor.snapshot_path.write_text(json.dumps(state))
    pages=[store.read(token,offset=i,limit=100,include_ui_context=True) for i in (0,100,200)]
    assert [r['accrued_output_raw'] for p in pages for r in p['rows']]==list(range(217))
    assert all(p['capture']['request_id']==meta['request_id'] and p['capture']['tick']==12 and
               p['capture']['captured_at']==meta['captured_at'] and p['captured_ui_context']['active_view']=='settlement' for p in pages)
    assert pages[0]['current_state']['scene']['active_view']=='world' and pages[-1]['next_offset'] is None and len(calls)==1


@pytest.mark.parametrize('failure',['cursor','errors','missing','scan','rows','bytes','metadata'])
def test_failed_capture_does_not_evict_good_capture(regional,failure):
    store,_,_,payload,_,spec=regional
    token=store.create(spec)['capture']['capture_id']
    if failure=='cursor':payload['data']['next_cursor']=217
    if failure=='errors':payload['data']['cell_errors']=1
    if failure=='missing':payload['data'].pop('next_cursor')
    if failure=='scan':payload['data']['scanned_cells']=216
    if failure=='rows':spec={**spec,'max_rows':216}
    if failure=='bytes':payload['ui_context']['text']='x'*(2*1024*1024)
    if failure=='metadata':payload['scene']['text']='x'*65536
    with pytest.raises(ValueError):store.create(spec)
    assert len(store._captures)==1 and store.read(token)['capture']['capture_id']==token


def test_separate_pools_expiry_and_same_session_freshness(regional,monkeypatch):
    store,advisor,state,_,_,spec=regional;clock=[0.]
    monkeypatch.setattr('syx_capture.time.monotonic',lambda:clock[0])
    tokens=[store.create(spec)['capture']['capture_id'] for _ in range(4)]
    with pytest.raises(ValueError,match='evicted'):store.read(tokens[0])
    for other in (TileCaptures(advisor),EntityCaptures(advisor),RegionalCaptures(advisor)):
        with pytest.raises(ValueError,match='missing'):other.read(tokens[-1])
    clock[0]=120
    with pytest.raises(ValueError,match='expired'):store.read(tokens[-1])
    token=store.create(spec)['capture']['capture_id']
    state['captured_at']=(datetime.now(timezone.utc)-timedelta(seconds=90)).isoformat();advisor.snapshot_path.write_text(json.dumps(state))
    with pytest.raises(ValueError,match='fresh'):store.read(token)
    state.update(captured_at=datetime.now(timezone.utc).isoformat(),session_id=str(uuid4()));advisor.snapshot_path.write_text(json.dumps(state))
    with pytest.raises(ValueError,match='session/version'):store.read(token)
    with pytest.raises(ValueError,match='missing'):store.read(token)
