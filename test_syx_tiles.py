from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json
import threading
import time
from uuid import uuid4

import pytest
from pydantic import ValidationError
from syx_tiles import TileSelection, query_tiles
from test_syx_live import live


@pytest.mark.parametrize('spec',[
    {}, {'tile_bounds':[0,0,0,1]}, {'tile_bounds':[0,0,2,2],'fields':['private']},
    {'tile_bounds':[0,0,2,2],'limit':True}, {'tile_bounds':[0,0,2,2],'scan_limit':4097},
    {'tile_bounds':[0,0,2,2],'cursor':5}, {'tile_bounds':[0,0,2,2],'fields':['room','room']},
    {'tile_bounds':[0,0,2,2],'has_room':'false'},
    {'tile_bounds':[0,0,2,2],'room_blueprint_id':'X','has_room':False},
    {'tile_bounds':[0,0,2,2],'method':'placeFloor'},
])
def test_invalid_tile_selection_never_reaches_game(spec):
    with pytest.raises(ValidationError):TileSelection.model_validate(spec)


def test_tile_wire_escapes_unicode_keys_and_preserves_bool_and_rectangle():
    selection=TileSelection(tile_bounds=[1,2,4,6],has_room=False,terrain_id='x\nfields=private 😀')
    wire=selection.wire(str(uuid4()),str(uuid4()),int(time.time()*1000+8000))
    assert wire.count('\n')==15 and 'fields=private' not in wire
    assert 'has_room=false\n' in wire and 'bounds=1,2,4,6\n' in wire


def responder(directory,stop,transform):
    seen=set()
    while not stop.is_set():
        try:
            parts=dict(line.split('=',1) for line in (directory/'tile-request.txt').read_text().splitlines())
            if parts['request_id'] not in seen:
                seen.add(parts['request_id'])
                result={'request_id':parts['request_id'],'session_id':parts['session'],'game_version':'0.71.44',
                    'captured_at':datetime.now(timezone.utc).isoformat(),'available':True,'read_mode':'tile_page',
                    'data':{'rows':[{'tile_x':2,'tile_y':4,'room':{'available':True,'data':None}}],
                        'scanned_tiles':2,'next_cursor':2,'predicate_errors':0,
                        'bounds':[2,4,5,5],'cursor_kind':'row_major_rectangle_offset'}}
                temp=directory/'tile-test.tmp';temp.write_text(json.dumps(transform(result)));temp.replace(directory/'tile-response.json')
        except FileNotFoundError:pass
        time.sleep(.005)


def run_response(advisor,transform=lambda x:x):
    stop=threading.Event()
    with ThreadPoolExecutor(max_workers=1) as pool:
        worker=pool.submit(responder,advisor.snapshot_path.parent,stop,transform)
        try:return query_tiles(advisor,{'tile_bounds':[2,4,5,5],'fields':['room']},timeout=1)
        finally:stop.set();worker.result(timeout=1)


def test_tile_channel_uses_shared_freshness_guard_and_no_entity_mailbox(live):
    advisor,state=live
    result=run_response(advisor)
    assert result['data']['rows'][0]['room']=={'available':True,'data':None}
    assert not (advisor.snapshot_path.parent/'entity-request.txt').exists()
    state['demo']=True;advisor.snapshot_path.write_text(json.dumps(state))
    with pytest.raises(ValueError,match='non-demo'):query_tiles(advisor,{'tile_bounds':[0,0,1,1]})


@pytest.mark.parametrize('tamper,match',[
    (lambda r:{**r,'read_mode':'capture'},'identity/bounds'),
    (lambda r:{**r,'data':{**r['data'],'bounds':[0,0,3,1]}},'identity/bounds'),
    (lambda r:{**r,'data':{**r['data'],'scanned_tiles':4097}},'scan bound'),
    (lambda r:{**r,'data':{**r['data'],'next_cursor':3}},'cursor'),
    (lambda r:{**r,'data':{**r['data'],'next_cursor':None}},'cursor'),
    (lambda r:{**r,'data':{**r['data'],'predicate_errors':3}},'predicate'),
    (lambda r:{**r,'data':{**r['data'],'rows':[{'tile_x':5,'tile_y':4}]}},'coordinates'),
    (lambda r:{**r,'data':{**r['data'],'rows':[{'tile_x':4,'tile_y':4}]}},'position'),
    (lambda r:{**r,'data':{**r['data'],'rows':[{'tile_x':2,'tile_y':4}]*2}},'duplicate'),
])
def test_tile_response_rejects_wrong_scope_incomplete_cursors_and_coordinates(live,tamper,match):
    with pytest.raises(ValueError,match=match):run_response(live[0],tamper)
