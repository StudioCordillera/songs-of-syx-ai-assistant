from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json
import threading
import time
from uuid import uuid4
import pytest
from pydantic import ValidationError
from syx_regions import RegionalSelection,query_regional_outputs
from test_syx_live import live


@pytest.mark.parametrize('spec',[
 {},{'region_ids':[],'resource_ids':['grain']}, {'region_ids':[True],'resource_ids':['grain']},
 {'region_ids':[1023],'resource_ids':['grain']},{'region_ids':[0,0],'resource_ids':['grain']},
 {'region_ids':[0],'resource_ids':['grain','grain']},{'region_ids':[0],'resource_ids':['grain'],'cursor':2},
 {'region_ids':[0],'resource_ids':['grain'],'min_accrued_output':5,'max_accrued_output':4},
 {'region_ids':[0],'resource_ids':['grain'],'fields':['private']},
 {'region_ids':[0],'resource_ids':['grain'],'scan_limit':4097},
 {'region_ids':[0],'resource_ids':['grain'],'faction_id':-1},
 {'region_ids':[0],'resource_ids':['grain'],'method':'ship'}])
def test_invalid_regional_selection_never_reaches_game(spec):
    with pytest.raises(ValidationError):RegionalSelection.model_validate(spec)


def test_regional_wire_is_canonical_and_does_not_inject_resource_text():
    spec=RegionalSelection(region_ids=[0,17],resource_ids=['粮\nlimit=100 😀'],min_accrued_output=0)
    wire=spec.wire(str(uuid4()),str(uuid4()),int(time.time()*1000+8000))
    assert wire.count('\n')==13 and 'limit=100' not in wire and 'minimum=0\n' in wire
    assert 'regions=0,17\n' in wire
    wider=RegionalSelection(region_ids=[0],resource_ids=['😀'*98+str(i) for i in range(30)])
    with pytest.raises(ValueError,match='8 KiB'):wider.wire(str(uuid4()),str(uuid4()),int(time.time()*1000+8000))


def responder(directory,stop,transform):
    seen=set()
    while not stop.is_set():
        try:
            parts=dict(line.split('=',1) for line in (directory/'regional-request.txt').read_text().splitlines())
            if parts['request_id'] not in seen:
                seen.add(parts['request_id'])
                result={'request_id':parts['request_id'],'session_id':parts['session'],'game_version':'0.71.44',
                    'captured_at':datetime.now(timezone.utc).isoformat(),'available':True,'read_mode':'regional_capture' if parts['protocol']=='2' else 'regional_page',
                    'consistency':'one callback fixture',
                    'observer_phase':'GAME.addAfterUpdate','scope':'campaign_world_regions','coverage':'partial','tick':3,
                    'scene':{'active_view':'world'},'ui_context':{'available':True,'active_view':'world'},
                    'data':{'rows':[{'region_id':17,'resource_id':'grain','accrued_output_raw':0,'days_until_configured_output':0}],
                        'scanned_cells':1,'cell_errors':0,'next_cursor':None,'region_ids':[17],'resource_ids':['grain'],
                        'scanned_regions':203,'scanned_resources':42,'region_scan_limit':1023,'resource_scan_limit':1000,'cursor_kind':'requested_region_resource_matrix'}}
                temp=directory/'regional-test.tmp';temp.write_text(json.dumps(transform(result)));temp.replace(directory/'regional-response.json')
        except FileNotFoundError:pass
        time.sleep(.005)


def response(advisor,transform=lambda r:r,*,capture=False):
    stop=threading.Event()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(responder,advisor.snapshot_path.parent,stop,transform)
        try:return query_regional_outputs(advisor,{'region_ids':[17],'resource_ids':['grain']},timeout=1,capture=capture)
        finally:stop.set();future.result(timeout=1)


def test_regional_transport_ignores_missing_cached_rows_and_preserves_observed_zero(live):
    advisor,state=live
    state['domains']['world']['coverage']='partial'
    state['domains']['world']['data']={'regional_output_bookkeeping':{'coverage':'partial','rows':[],'truncated':True}}
    advisor.snapshot_path.write_text(json.dumps(state))
    r=response(advisor)
    assert r['data']['rows'][0]['accrued_output_raw']==0
    assert not (advisor.snapshot_path.parent/'entity-request.txt').exists()
    assert not (advisor.snapshot_path.parent/'tile-request.txt').exists()
    state['demo']=True;advisor.snapshot_path.write_text(json.dumps(state))
    with pytest.raises(ValueError,match='non-demo'):query_regional_outputs(advisor,{'region_ids':[17],'resource_ids':['grain']})


@pytest.mark.parametrize('tamper,match',[
 (lambda r:{**r,'scope':'city'},'identity/scope'),
 (lambda r:{**r,'data':{**r['data'],'region_ids':[1]}},'identity/scope'),
 (lambda r:{**r,'data':{**r['data'],'next_cursor':0}},'cursor'),
 (lambda r:{**r,'data':{**r['data'],'cell_errors':True}},'cell/error'),
 (lambda r:{**r,'data':{**r['data'],'scanned_resources':1001}},'registry'),
 (lambda r:{**r,'tick':True},'context'),
 (lambda r:{**r,'data':{**r['data'],'rows':[{'region_id':18,'resource_id':'grain','accrued_output_raw':0,'days_until_configured_output':0}]}},'identities'),
 (lambda r:{**r,'data':{**r['data'],'rows':[{'region_id':17,'resource_id':'grain','accrued_output_raw':-1,'days_until_configured_output':0}]}},'numeric'),
 (lambda r:{**r,'data':{**r['data'],'rows':[{'region_id':17,'resource_id':'grain','accrued_output_raw':0,'days_until_configured_output':0,'private':1}]}},'projection'),
])
def test_regional_response_rejects_mismatched_or_unbounded_data(live,tamper,match):
    with pytest.raises(ValueError,match=match):response(live[0],tamper)
