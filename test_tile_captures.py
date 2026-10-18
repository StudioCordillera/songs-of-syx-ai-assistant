from datetime import datetime,timezone,timedelta
import json
from uuid import uuid4
import pytest
from pydantic import ValidationError
from syx_capture import TileCaptures,EntityCaptures
from syx_tiles import TileCaptureSelection
from test_syx_capture import capture_setup


@pytest.fixture
def tiles(capture_setup,monkeypatch):
    _,advisor,state,_,_=capture_setup
    payload={'read_mode':'tile_page','request_id':str(uuid4()),'session_id':state['session_id'],
        'game_version':state['game_version'],'captured_at':state['captured_at'],'tick':12,
        'observer_phase':'GAME.addAfterUpdate','scope':'instantiated_settlement_scene',
        'scene':{'active_view':'settlement'},'ui_context':{'active_view':'settlement'},
        'consistency':'one mutable live page','data':{'rows':[
            {'tile_x':x,'tile_y':4,'room':{'available':False,'data':None,'reason':'fixture_getter_failure'}} for x in range(2,13)],
            'bounds':[2,4,13,5],'cursor_kind':'row_major_rectangle_offset','next_cursor':None,
            'scanned_tiles':11,'predicate_errors':0}}
    calls=[]
    def query(*args):calls.append(args);return json.loads(json.dumps(payload))
    monkeypatch.setattr('syx_tiles.query_tiles',query)
    return TileCaptures(advisor),advisor,state,payload,calls


def test_tile_pages_keep_original_coordinates_context_and_unknown_fields_without_game_reread(tiles):
    store,advisor,state,payload,calls=tiles
    meta=store.create({'tile_bounds':[2,4,13,5],'fields':['room']})['capture']
    token=meta['capture_id'];assert meta['selection_complete'] and meta['capture_kind']=='tile'
    assert meta['row_count']==11 and meta['request_id']==payload['request_id']
    first=store.read(token,limit=4,include_ui_context=True)
    first['rows'][0]['tile_x']=99
    payload['data']['rows'][0]['tile_x']=98
    state.update(tick=900,scene={'active_view':'world'})
    advisor.snapshot_path.write_text(json.dumps(state))
    pages=[store.read(token,offset=i,limit=4,include_ui_context=True) for i in [0,4,8]]
    assert [r['tile_x'] for p in pages for r in p['rows']]==list(range(2,13))
    assert all(p['capture']['tick']==12 and p['capture']['captured_at']==meta['captured_at'] for p in pages)
    assert all(p['captured_ui_context']['active_view']=='settlement' for p in pages)
    assert pages[0]['rows'][0]['room']['available'] is False
    assert pages[0]['current_state']['scene']['active_view']=='world'
    assert pages[-1]['next_offset'] is None and len(calls)==1


@pytest.mark.parametrize('kind',['cursor','scan','predicate','boolean_error','bytes'])
def test_tile_capture_failures_retain_nothing(tiles,kind):
    store,_,_,payload,_=tiles
    if kind=='cursor':payload['data']['next_cursor']=11
    if kind=='scan':payload['data']['scanned_tiles']=10
    if kind=='predicate':payload['data']['predicate_errors']=1
    if kind=='boolean_error':payload['data']['predicate_errors']=False
    if kind=='bytes':payload['ui_context']['text']='x'*65536
    with pytest.raises(ValueError,match='Incomplete|64 KiB'):store.create({'tile_bounds':[2,4,13,5]})
    assert not store._captures


@pytest.mark.parametrize('overrides',[{'tile_bounds':[0,0,4097,1]},{'scan_limit':10},{'max_rows':101},
    {'max_rows':True},{'cursor':1},{'limit':100},{'fields':['room','room']}])
def test_invalid_tile_capture_never_calls_backend(tiles,overrides):
    store,_,_,_,calls=tiles
    with pytest.raises(ValidationError):store.create({'tile_bounds':[2,4,13,5],**overrides})
    assert not calls


def test_tile_token_pools_expiry_and_changed_session(tiles,monkeypatch):
    store,advisor,state,_,_=tiles;clock=[0.]
    monkeypatch.setattr('syx_capture.time.monotonic',lambda:clock[0])
    tokens=[store.create({'tile_bounds':[2,4,13,5]})['capture']['capture_id'] for _ in range(4)]
    with pytest.raises(ValueError,match='evicted'):store.read(tokens[0])
    with pytest.raises(ValueError,match='missing'):EntityCaptures(advisor).read(tokens[-1])
    with pytest.raises(ValueError,match='missing'):TileCaptures(advisor).read(tokens[-1])
    clock[0]=120
    with pytest.raises(ValueError,match='expired'):store.read(tokens[-1])
    token=store.create({'tile_bounds':[2,4,13,5]})['capture']['capture_id']
    state['session_id']=str(uuid4());advisor.snapshot_path.write_text(json.dumps(state))
    with pytest.raises(ValueError,match='session/version'):store.read(token)
    with pytest.raises(ValueError,match='missing'):store.read(token)


def test_tile_stale_or_different_version_reads_are_refused(tiles):
    store,advisor,state,_,_=tiles
    token=store.create({'tile_bounds':[2,4,13,5]})['capture']['capture_id']
    state['captured_at']=(datetime.now(timezone.utc)-timedelta(seconds=90)).isoformat()
    advisor.snapshot_path.write_text(json.dumps(state))
    with pytest.raises(ValueError,match='fresh'):store.read(token)
    state.update(captured_at=datetime.now(timezone.utc).isoformat(),game_version='changed')
    advisor.snapshot_path.write_text(json.dumps(state))
    with pytest.raises(ValueError,match='session/version'):store.read(token)
