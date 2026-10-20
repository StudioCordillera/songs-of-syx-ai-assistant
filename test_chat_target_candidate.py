"""Detached target drafts against real encoded capture pools; game reads synthetic."""
from datetime import datetime, timezone, timedelta
import json
from uuid import uuid4

import pytest

from dev.chat_target_candidate import TargetDrafts, canonical
from syx_capture import EntityCaptures, TileCaptures, RegionalCaptures
from test_syx_capture import capture_setup


@pytest.fixture
def targets(capture_setup, monkeypatch):
    entities, advisor, state, payload, calls = capture_setup
    state['scene'] = {'active_view': 'settlement'}
    advisor.snapshot_path.write_text(json.dumps(state))
    tiles, regions = TileCaptures(advisor), RegionalCaptures(advisor)
    tile_payload = {**payload, 'request_id': str(uuid4()), 'tick': 2,
                    'data': {'bounds': [0, 0, 2, 1], 'scanned_tiles': 2,
                             'predicate_errors': 0, 'next_cursor': None,
                             'rows': [{'tile_x': x, 'tile_y': 0,
                                       'room': {'available': False, 'data': None}} for x in range(2)]}}
    region_payload = {**payload, 'request_id': str(uuid4()), 'tick': 3,
                      'data': {'scanned_cells': 1, 'cell_errors': 0, 'next_cursor': None,
                               'rows': [{'region_id': 1, 'resource_id': 'grain', 'accrued_output_raw': 5}]}}
    monkeypatch.setattr('syx_tiles.query_tiles', lambda *a: json.loads(json.dumps(tile_payload)))
    monkeypatch.setattr('syx_regions.query_regional_outputs', lambda *a, **k: json.loads(json.dumps(region_payload)))
    tokens = {'entity': entities.create({'fields': ['id', 'tile_x']})['capture']['capture_id'],
              'tile': tiles.create({'tile_bounds': [0, 0, 2, 1], 'fields': ['room']})['capture']['capture_id'],
              'regional_output': regions.create({'region_ids': [1], 'resource_ids': ['grain']})['capture']['capture_id']}
    return TargetDrafts(entities, tiles, regions), tokens, advisor, state, payload, calls


def save_state(advisor, state):
    advisor.snapshot_path.write_text(json.dumps(state))


def test_typed_pages_keep_separate_original_provenance_and_unknowns(targets):
    drafts, tokens, advisor, state, payload, calls = targets
    chat = str(uuid4())
    for kind, token in tokens.items():
        drafts.stage(chat, kind, token)
    state['tick'] = 99
    payload['data']['rows'][0]['tile_x'] = 999
    save_state(advisor, state)
    envelope = drafts.prepare(chat)
    rows = envelope['attachments']
    assert [r['kind'] for r in rows] == ['entity', 'tile', 'regional_output']
    assert [r['capture']['tick'] for r in rows] == [1, 2, 3]
    assert rows[0]['rows'] == [{'id': 0, 'tile_x': 0}]
    assert rows[1]['rows'][0]['room'] == {'available': False, 'data': None}
    assert rows[0]['next_offset'] == 1  # page, never a claim of all rows
    assert rows[2]['next_offset'] is None
    assert 'historical' in envelope['notice'] and 'transaction' in envelope['notice']
    assert len(calls) == 1  # paging did not invoke synthetic entity game reader again
    envelope['attachments'][0]['rows'][0]['id'] = 200
    assert drafts.prepare(chat)['attachments'][0]['rows'][0]['id'] == 0
    assert len(drafts.preview(chat)) == 3  # prepare never enqueues/consumes


def test_chat_isolation_duplicate_and_wrong_chat_removal(targets):
    drafts, tokens, *_ = targets
    a, b = str(uuid4()), str(uuid4())
    item = drafts.stage(a, 'entity', tokens['entity'])
    assert drafts.preview(b) == []
    with pytest.raises(ValueError, match='already attached'):
        drafts.stage(a, 'entity', tokens['entity'])
    with pytest.raises(ValueError, match='this chat'):
        drafts.remove(b, item['attachment_id'])
    drafts.remove(a, item['attachment_id'])
    assert drafts.preview(a) == [] and a not in drafts._drafts


@pytest.mark.parametrize('change', ['runtime', 'version', 'scene', 'stale', 'unloaded', 'demo'])
def test_send_refuses_transition_but_retains_removable_historical_preview(targets, change):
    drafts, tokens, advisor, state, *_ = targets
    chat = str(uuid4())
    item = drafts.stage(chat, 'entity', tokens['entity'])
    if change == 'runtime': state['session_id'] = str(uuid4())
    elif change == 'version': state['game_version'] = '0.72.0'
    elif change == 'scene': state['scene'] = {'active_view': 'world'}
    elif change == 'stale': state['captured_at'] = (datetime.now(timezone.utc) - timedelta(seconds=100)).isoformat()
    elif change == 'unloaded': state['game_loaded'] = False
    else: state['demo'] = True
    save_state(advisor, state)
    with pytest.raises(ValueError): drafts.prepare(chat)
    assert drafts.preview(chat) == [item]
    drafts.remove(chat, item['attachment_id'])


def test_stage_refuses_historical_scene_even_when_capture_pool_allows_pages(targets):
    drafts, tokens, advisor, state, *_ = targets
    state['scene'] = {'active_view': 'world'}
    save_state(advisor, state)
    with pytest.raises(ValueError, match='scene changed'):
        drafts.stage(str(uuid4()), 'entity', tokens['entity'])
    assert drafts._drafts == {}


def test_expiry_restart_and_wrong_pool_fail_without_partial_pack(targets, monkeypatch):
    drafts, tokens, *_ = targets
    chat = str(uuid4())
    drafts.stage(chat, 'entity', tokens['entity'])
    with pytest.raises(ValueError, match='missing'):
        drafts.stage(chat, 'tile', tokens['entity'])
    new = TargetDrafts(EntityCaptures(drafts.advisor), TileCaptures(drafts.advisor), RegionalCaptures(drafts.advisor))
    with pytest.raises(ValueError, match='missing'):
        new.stage(chat, 'entity', tokens['entity'])
    monkeypatch.setattr('syx_capture.time.monotonic', lambda: 10**15)
    with pytest.raises(ValueError, match='expired'):
        drafts.prepare(chat)
    assert len(drafts.preview(chat)) == 1


@pytest.mark.parametrize('args', [
    ('hover', 0, 1), ('resource', 0, 1), ('entity', True, 1),
    ('entity', -1, 1), ('entity', 0, False), ('entity', 0, 101), ('entity', 11, 1),
])
def test_unsupported_and_bad_pages_do_not_mutate_drafts(targets, args):
    drafts, tokens, *_ = targets
    kind, offset, limit = args
    with pytest.raises(ValueError):
        drafts.stage(str(uuid4()), kind, tokens['entity'], offset=offset, limit=limit)
    assert drafts._drafts == {}


def test_observed_switch_during_prepare_refuses_whole_envelope(targets, monkeypatch):
    drafts, tokens, advisor, state, *_ = targets
    chat = str(uuid4())
    drafts.stage(chat, 'entity', tokens['entity'])
    original = drafts.pools['entity'].read
    def switched(*a, **kw):
        result = original(*a, **kw)
        state['session_id'] = str(uuid4())
        save_state(advisor, state)
        return result
    monkeypatch.setattr(drafts.pools['entity'], 'read', switched)
    with pytest.raises(ValueError, match='while preparing'):
        drafts.prepare(chat)
    assert len(drafts.preview(chat)) == 1


def test_own_payload_tampering_is_refused_at_send(targets):
    drafts, tokens, *_ = targets
    chat = str(uuid4())
    drafts.stage(chat, 'entity', tokens['entity'])
    pool = drafts.pools['entity']
    created, raw = pool._captures[tokens['entity']]
    payload = json.loads(raw)
    payload['data']['rows'][0]['tile_x'] = 88
    pool._captures[tokens['entity']] = created, canonical(payload)
    with pytest.raises(ValueError, match='evidence changed'):
        drafts.prepare(chat)


def test_byte_cap_and_attachment_cap_are_atomic(targets):
    drafts, tokens, *_ = targets
    chat = str(uuid4())
    for i in range(8): drafts.stage(chat, 'entity', tokens['entity'], offset=i)
    with pytest.raises(ValueError, match='eight'): drafts.stage(chat, 'entity', tokens['entity'], offset=8)
    assert len(drafts.preview(chat)) == 8
    other = str(uuid4())
    pool = drafts.pools['entity']
    created, raw = pool._captures[tokens['entity']]
    payload = json.loads(raw)
    payload['data']['rows'][0]['note'] = 'é' * 16500  # cap measures UTF-8, not characters
    pool._captures[tokens['entity']] = created, canonical(payload)
    with pytest.raises(ValueError, match='32 KiB'):
        drafts.stage(other, 'entity', tokens['entity'])
    assert other not in drafts._drafts


def test_draft_chat_cap_has_no_silent_eviction(targets):
    drafts, tokens, *_ = targets
    for _ in range(100): drafts.stage(str(uuid4()), 'entity', tokens['entity'])
    with pytest.raises(ValueError, match='100 draft chats'):
        drafts.stage(str(uuid4()), 'entity', tokens['entity'])
    assert len(drafts._drafts) == 100


def test_fixed_pool_constructor_and_chat_ids(targets):
    drafts, tokens, *_ = targets
    with pytest.raises(ValueError, match='fixed production'):
        TargetDrafts(None, None, None)
    with pytest.raises(ValueError, match='same advisor'):
        TargetDrafts(drafts.pools['entity'], TileCaptures(object()), drafts.pools['regional_output'])
    with pytest.raises(ValueError, match='UUID'):
        drafts.stage('../other', 'entity', tokens['entity'])


@pytest.mark.parametrize('scene', [None, {}, {'active_view': ''}, {'active_view': 'unknown'}, {'active_view': False}])
def test_unknown_scene_refuses_stage(targets, monkeypatch, scene):
    drafts, tokens, advisor, *_ = targets
    original = advisor.status
    monkeypatch.setattr(advisor, 'status', lambda *a: {**original(*a), 'scene': scene})
    with pytest.raises(ValueError, match='Known'):
        drafts.stage(str(uuid4()), 'entity', tokens['entity'])
    assert drafts._drafts == {}


def test_aggregate_byte_cap_preserves_previously_staged_target(targets):
    drafts, tokens, *_ = targets
    pool = drafts.pools['entity']
    created, raw = pool._captures[tokens['entity']]
    payload = json.loads(raw)
    for row in payload['data']['rows'][:2]: row['note'] = 'x' * 18000
    pool._captures[tokens['entity']] = created, canonical(payload)
    chat = str(uuid4())
    first = drafts.stage(chat, 'entity', tokens['entity'])
    with pytest.raises(ValueError, match='32 KiB'):
        drafts.stage(chat, 'entity', tokens['entity'], offset=1)
    assert drafts.prepare(chat)['attachments'] == [first]


def test_same_active_view_changed_scene_kind_is_refused(targets):
    drafts, tokens, advisor, state, *_ = targets
    chat = str(uuid4())
    drafts.stage(chat, 'entity', tokens['entity'])
    state['scene']['settlement_scene_kind'] = 'battlefield'
    save_state(advisor, state)
    with pytest.raises(ValueError, match='scene changed'):
        drafts.prepare(chat)
    assert len(drafts.preview(chat)) == 1


def test_staged_eviction_preserves_removable_preview(targets):
    drafts, tokens, *_ = targets
    chat = str(uuid4())
    item = drafts.stage(chat, 'entity', tokens['entity'])
    assert item['retention_hint']['remaining_seconds_at_stage'] > 0
    assert 'not revalidated' in item['retention_hint']['notice']
    for _ in range(3): drafts.pools['entity'].create({})
    with pytest.raises(ValueError, match='evicted'): drafts.prepare(chat)
    assert drafts.preview(chat) == [item]
    drafts.remove(chat, item['attachment_id'])
    assert drafts.preview(chat) == []


def test_observed_scene_or_runtime_failure_can_recover_without_reading_shared_pool(targets):
    drafts, tokens, advisor, state, *_ = targets
    chat = str(uuid4()); original_runtime = state['session_id']
    drafts.stage(chat, 'entity', tokens['entity'])
    for change in ['scene', 'runtime']:
        if change == 'scene': state['scene'] = {'active_view': 'world'}
        else: state['session_id'] = str(uuid4())
        save_state(advisor, state)
        with pytest.raises(ValueError): drafts.prepare(chat)
        assert tokens['entity'] in drafts.pools['entity']._captures
        state['scene'] = {'active_view': 'settlement'}; state['session_id'] = original_runtime
        save_state(advisor, state)
        assert drafts.prepare(chat)['has_attachments'] is True


def test_overlap_refused_and_empty_preparation_explicit(targets):
    drafts, tokens, *_ = targets
    chat = str(uuid4())
    assert drafts.prepare(chat)['has_attachments'] is False
    drafts.stage(chat, 'entity', tokens['entity'], limit=2)
    with pytest.raises(ValueError, match='overlap'):
        drafts.stage(chat, 'entity', tokens['entity'], offset=1)
    assert len(drafts.preview(chat)) == 1


def test_nonfinite_field_refuses_actionably_without_changing_evidence(targets):
    drafts, tokens, *_ = targets
    pool = drafts.pools['entity'];created, raw = pool._captures[tokens['entity']]
    payload = json.loads(raw);payload['data']['rows'][0]['stat'] = float('nan')
    pool._captures[tokens['entity']] = created, json.dumps(payload).encode()
    with pytest.raises(ValueError, match='non-finite.*narrow'):
        drafts.stage(str(uuid4()), 'entity', tokens['entity'])
    assert drafts._drafts == {} and tokens['entity'] in pool._captures
