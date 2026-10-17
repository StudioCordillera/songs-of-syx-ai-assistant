from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from syx_capture import EntityCaptures
from syx_live import EntityCaptureSelection
from syx_mcp import Advisor


@pytest.fixture
def capture_setup(tmp_path, monkeypatch):
    state = json.loads((Path(__file__).parent / 'snapshot.example.json').read_text())
    state.update(demo=False, game_loaded=True, game_version='0.71.44', session_id=str(uuid4()),
                 captured_at=datetime.now(timezone.utc).isoformat())
    path = tmp_path / 'snapshot.json'
    path.write_text(json.dumps(state))
    advisor = Advisor(path, tmp_path / 'corpus.json')
    payload = {'read_mode':'capture', 'session_id':state['session_id'], 'game_version':state['game_version'],
               'captured_at':state['captured_at'], 'tick':1, 'scope':'instantiated_settlement_scene',
               'scene':{'active_view':'settlement'}, 'ui_context':{'active_view':'settlement'},
               'consistency':'one update observation', 'data':{'rows':[{'id':i,'tile_x':i} for i in range(11)],
               'next_cursor':None,'scanned_slots':60000,'predicate_errors':0}}
    calls = []
    def read(*args):
        calls.append(args)
        return json.loads(json.dumps(payload))
    monkeypatch.setattr('syx_capture.capture_entities', read)
    return EntityCaptures(advisor), advisor, state, payload, calls


def test_retained_pages_do_not_follow_backend_changes_or_response_mutation(capture_setup):
    store, advisor, state, payload, calls = capture_setup
    info = store.create({'fields':['id','tile_x']})
    token = info['capture']['capture_id']
    assert info['capture']['row_count'] == 11 and 'rows' not in info
    first = store.read(token, limit=4, include_ui_context=True)
    # Both the game observation and a previous returned response change after capture.
    payload['data']['rows'].append({'id':99,'tile_x':99})
    payload['data']['rows'][0]['tile_x'] = 999
    first['rows'][0]['tile_x'] = 888
    state['tick'] = 900
    state['scene'] = {'active_view':'world'}
    advisor.snapshot_path.write_text(json.dumps(state))
    pages = [store.read(token, offset=offset, limit=4, include_ui_context=True) for offset in (0,4,8)]
    assert [row['id'] for page in pages for row in page['rows']] == list(range(11))
    assert pages[0]['rows'][0]['tile_x'] == 0
    assert all(page['capture']['tick'] == 1 and page['capture']['captured_at'] == payload['captured_at'] for page in pages)
    assert all(page['captured_ui_context']['active_view'] == 'settlement' for page in pages)
    assert pages[0]['current_state']['scene']['active_view'] == 'world'
    assert pages[-1]['next_offset'] is None and len(calls) == 1


def test_capture_expiry_eviction_and_cross_server_tokens(capture_setup, monkeypatch):
    store, advisor, _, _, _ = capture_setup
    clock = [0.0]
    monkeypatch.setattr('syx_capture.time.monotonic', lambda:clock[0])
    tokens = [store.create({})['capture']['capture_id'] for _ in range(4)]
    with pytest.raises(ValueError, match='evicted'):store.read(tokens[0])
    assert store.read(tokens[-1])['rows']
    with pytest.raises(ValueError, match='missing'):EntityCaptures(advisor).read(tokens[-1])
    clock[0] = 120.0
    with pytest.raises(ValueError, match='expired'):store.read(tokens[-1])


def test_capture_session_change_and_stale_observation_are_rejected(capture_setup):
    store, advisor, state, _, _ = capture_setup
    token = store.create({})['capture']['capture_id']
    state['captured_at'] = (datetime.now(timezone.utc)-timedelta(seconds=90)).isoformat()
    advisor.snapshot_path.write_text(json.dumps(state))
    with pytest.raises(ValueError, match='fresh'):store.read(token)
    state['captured_at'] = datetime.now(timezone.utc).isoformat()
    state['session_id'] = str(uuid4())
    advisor.snapshot_path.write_text(json.dumps(state))
    with pytest.raises(ValueError, match='session/version'):store.read(token)
    with pytest.raises(ValueError, match='missing'):store.read(token)


def test_partial_oversized_and_unidentified_captures_retain_nothing(capture_setup):
    store, _, _, payload, _ = capture_setup
    payload['data']['next_cursor'] = 20
    with pytest.raises(ValueError, match='Incomplete'):store.create({})
    payload['data']['next_cursor'] = None
    payload['data']['rows'] = [{'id':1}, {'id':1}]
    with pytest.raises(ValueError, match='unique'):store.create({})
    payload['data']['rows'] = [{'id':1,'text':'x'*(2*1024*1024)}]
    with pytest.raises(ValueError, match='2 MiB'):store.create({})
    assert not store._captures


def test_oversized_page_can_be_retried_without_recapture(capture_setup):
    store, _, _, payload, calls = capture_setup
    payload['data']['rows'] = [{'id':i,'text':'x'*20000} for i in range(6)]
    token = store.create({})['capture']['capture_id']
    with pytest.raises(ValueError, match='64 KiB'):store.read(token, limit=6)
    assert len(store.read(token, limit=2)['rows']) == 2 and len(calls) == 1


@pytest.mark.parametrize('spec', [{'cursor':1},{'max_rows':2001},{'scan_limit':100001},
                                  {'fields':['tile_x']},{'limit':100},
                                  {'fields':['id','stats'],'stat_ids':[1,2,3],'max_rows':2000}])
def test_capture_selection_bounds(spec):
    with pytest.raises(ValidationError):EntityCaptureSelection.model_validate(spec)


def test_capture_protocol_is_distinct_and_bounded():
    selection = EntityCaptureSelection(fields=['id','stats'],stat_ids=[1,2],max_rows=2000)
    wire = selection.wire(str(uuid4()),str(uuid4()),1234567890123)
    assert wire.startswith('protocol=2\n') and wire.count('\n') == 15
    assert 'limit=2000\n' in wire and 'scan_limit=100000\n' in wire
