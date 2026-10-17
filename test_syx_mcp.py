import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import ValidationError

from syx_mcp import Advisor, Snapshot, Source

ROOT = Path(__file__).parent

@pytest.fixture
def setup(tmp_path):
    state = json.loads((ROOT / 'snapshot.example.json').read_text())
    state['captured_at'] = datetime.now(timezone.utc).isoformat()
    snapshot = tmp_path / 'snapshot.json'
    snapshot.write_text(json.dumps(state))
    return Advisor(snapshot, tmp_path / 'corpus.json'), state


def save(advisor, state):
    advisor.snapshot_path.write_text(json.dumps(state))


def test_missing_game(tmp_path):
    assert Advisor(tmp_path / 'missing', tmp_path / 'corpus').status()['available'] is False


def test_demo_never_live(setup):
    a, _ = setup
    assert a.status()['live'] is False
    result = a.query('resources', '/stockpiles')
    assert result['state']['demo'] is True
    assert result['data'][0]['amount'] == 123


def test_live_freshness_and_unload(setup):
    a, s = setup
    s['demo'] = False
    save(a, s)
    assert a.status()['live'] is True
    s['captured_at'] = (datetime.now(timezone.utc) - timedelta(seconds=90)).isoformat()
    save(a, s)
    assert a.status()['live'] is False
    with pytest.raises(ValueError, match='fresh'):
        a.query('resources')
    s['captured_at'] = datetime.now(timezone.utc).isoformat()
    s['game_loaded'] = False
    save(a, s)
    with pytest.raises(ValueError, match='loaded'):
        a.query('resources')


def test_future_clock_is_not_live(setup):
    a, s = setup
    s['demo'] = False
    s['captured_at'] = (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat()
    save(a, s)
    assert a.status()['live'] is False


def test_session_consistency_and_unavailable(setup):
    a, _ = setup
    with pytest.raises(ValueError, match='changed'):
        a.query('resources', expected_snapshot_id='other-session')
    with pytest.raises(ValueError, match='unavailable'):
        a.query('military')


def test_pagination_and_escaped_pointer(setup):
    a, s = setup
    s['domains']['resources']['data'] = {'a/b': {'~x': list(range(120))}}
    save(a, s)
    result = a.query('resources', '/a~1b/~0x', offset=50, limit=50)
    assert result['data'] == list(range(50, 100))
    assert result['next_offset'] == 100
    assert a.query('resources', '/a~1b/~0x', 100, 50)['next_offset'] is None
    with pytest.raises(ValueError):
        a.query('../auth.json')
    with pytest.raises(ValueError):
        a.query('resources', limit=101)


def test_coverage_validation_and_corruption(setup):
    a, s = setup
    del s['domains']['military']
    with pytest.raises(ValidationError):
        Snapshot.model_validate(s)
    a.snapshot_path.write_text('{')
    assert a.status()['available'] is False


def test_bounded_result(setup):
    a, s = setup
    s['domains']['resources']['data'] = {'large': 'a' * 65537}
    save(a, s)
    with pytest.raises(ValueError, match='large'):
        a.query('resources')


def test_corpus_citations_and_version(setup):
    a, _ = setup
    assert a.search('food')['results'] == []
    # Test-only invented evidence, never shipped as a gameplay guide.
    record = {'id': 'test-1', 'title': 'Test fixture', 'url': 'https://example.com/test-only',
              'kind': 'guide', 'retrieved_at': datetime.now(timezone.utc).isoformat(),
              'game_versions': ['TEST-A'], 'text': 'Food fixture text; not a game fact.'}
    a.corpus_path.write_text(json.dumps([record]))
    result = a.search('food', 'TEST-B')['results'][0]
    assert result['version_compatibility'] == 'mismatch'
    assert result['url'] == record['url']
    record['url'] = 'file:///etc/passwd'
    with pytest.raises(ValidationError):
        Source.model_validate(record)


def test_mcp_transport(setup):
    a, state = setup
    state['ui_context']={'available':True,'coverage':'partial','active_view':'settlement','overlay_order_known':False}
    state['references']=[{'id':'stat:95487','category':'stat','title':'Fixture food',
        'text':'Test fixture only, not a gameplay fact.','origin':'test fixture'}]
    save(a,state)
    async def exercise():
        params = StdioServerParameters(command=sys.executable,
            args=['-m', 'syx_mcp'], cwd=str(ROOT),
            env={**os.environ, 'SYX_STATE_DIR': str(a.snapshot_path.parent)})
        async with stdio_client(params) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                listing = await session.list_tools()
                assert {t.name for t in listing.tools} == {
                    'game_query_help', 'game_status', 'query_game_state', 'search_guidance',
                    'describe_game_fields', 'select_game_state', 'search_game_references', 'get_game_ui_context', 'get_game_api_support', 'query_live_entities', 'capture_live_entities', 'read_entity_capture'}
                assert all(t.annotations.read_only_hint for t in listing.tools)
                assert next(t for t in listing.tools if t.name=="capture_live_entities").annotations.idempotent_hint is False
                result = await session.call_tool('game_status', {})
                assert not result.is_error
                assert 'demo-session' in str(result)
                query = await session.call_tool('query_game_state', {
                    'domain': 'resources', 'pointer': '/stockpiles'})
                assert not query.is_error
                selection = await session.call_tool('select_game_state', {'spec':{'queries':[
                    {'source':{'domain':'resources','path':'/stockpiles'},
                     'select':{'amount':{'field':'/amount'}},'limit':1}]}})
                assert not selection.is_error and '123' in str(selection)
                help_result = await session.call_tool('game_query_help', {})
                assert not help_result.is_error and 'binary_operators' in str(help_result)
                references = await session.call_tool('search_game_references', {'query':'food'})
                assert not references.is_error and 'stat:95487' in str(references)
                exact_reference = await session.call_tool('search_game_references', {'query':'stat:95487','category':'stat'})
                assert not exact_reference.is_error and 'Fixture food' in str(exact_reference)
                context = await session.call_tool('get_game_ui_context', {})
                assert not context.is_error and 'settlement' in str(context)
                live_read = await session.call_tool('query_live_entities', {'spec':{}})
                assert live_read.is_error and 'non-demo' in str(live_read)
                capture = await session.call_tool('capture_live_entities', {'spec':{}})
                assert capture.is_error and 'non-demo' in str(capture)
                missing_capture = await session.call_tool('read_entity_capture', {'capture_id':str(__import__('uuid').uuid4())})
                assert missing_capture.is_error and 'missing' in str(missing_capture).lower()
                support = await session.call_tool('get_game_api_support', {'query':'selected_room_instance'})
                assert not support.is_error and 'unavailable' in str(support)
                state['demo']=False
                state['captured_at']=(datetime.now(timezone.utc)-timedelta(seconds=90)).isoformat()
                save(a,state)
                stale_context = await session.call_tool('get_game_ui_context', {})
                assert stale_context.is_error

                invalid = await session.call_tool('query_game_state', {'domain': '../secret'})
                assert invalid.is_error
    asyncio.run(exercise())


def test_stale_state_is_unknown_not_currently_loaded(setup):
    advisor,state=setup
    state['demo']=False
    state['captured_at']=(datetime.now(timezone.utc)-timedelta(seconds=90)).isoformat()
    save(advisor,state)
    status=advisor.status()
    assert status['game_loaded'] is None and status['observed_game_loaded'] is True
    assert status['state_certainty']=='unknown_updates_stopped'


def test_scene_scope_is_preserved_and_setup_placeholders_rejected(setup):
    a,state=setup
    state['scene']={'active_view':'world_generation','settlement_exists':False,
                    'settlement_scene_kind':'unavailable'}
    state['domains']['resources']={'coverage':'unavailable','reason':'Not generated',
                                   'scope':'instantiated_settlement_scene','data':None}
    save(a,state)
    assert a.status()['scene']['settlement_exists'] is False
    assert a.status()['coverage']['resources']['scope']=='instantiated_settlement_scene'
    with pytest.raises(ValueError,match='unavailable'):
        a.select({'queries':[{'source':{'domain':'resources'}}]})


def test_select_can_return_context_without_mixing_snapshots(setup):
    advisor,state=setup
    state['ui_context']={'available':True,'known_overlays':{'confirmation':True},
                         'selected_subject':{'entity_id':8}}
    state['domains']['entities']={'coverage':'partial','reason':'synthetic fixture',
        'scope':'instantiated_settlement_scene','data':{'items':[{'id':8}]}}
    save(advisor,state)
    result=advisor.select({'queries':[{'source':{'domain':'entities','path':'/items'},
        'where':{'eq':[{'field':'/id'},{'context':'/selected_subject/entity_id'}]}}],
        'include_ui_context':True})
    assert result['ui_context']['known_overlays']['confirmation'] is True
    assert result['results'][0]['rows']==[{'id':8}]
    assert result['state']['snapshot_id']==state['snapshot_id']
