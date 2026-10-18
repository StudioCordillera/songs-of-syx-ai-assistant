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
                    'describe_game_fields', 'select_game_state', 'search_game_references', 'get_game_ui_context', 'get_game_api_support', 'query_live_entities', 'capture_live_entities', 'read_entity_capture','query_live_tiles','capture_live_tiles','read_tile_capture','query_live_regional_outputs','capture_live_regional_outputs','read_regional_output_capture'}
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
                bad_shape=await session.call_tool('select_game_state',{'spec':{'queries':[{'domain':'resources'}]}})
                assert bad_shape.is_error and 'Invalid query fields' in str(bad_shape)
                old_selection=await session.call_tool('select_game_state',{'spec':{'expected_snapshot_id':'old-id','queries':[{'source':{'domain':'resources'}}]}})
                assert old_selection.is_error and 'Snapshot changed' in str(old_selection)

                references = await session.call_tool('search_game_references', {'query':'food'})
                assert not references.is_error and 'stat:95487' in str(references)
                exact_reference = await session.call_tool('search_game_references', {'query':'stat:95487','category':'stat'})
                assert not exact_reference.is_error and 'Fixture food' in str(exact_reference)
                context = await session.call_tool('get_game_ui_context', {})
                assert not context.is_error and 'settlement' in str(context)
                tile_read = await session.call_tool('query_live_tiles', {'spec':{'tile_bounds':[0,0,1,1]}})
                assert tile_read.is_error
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

                state['references']=[{'id':'room:large'+str(i),'category':'room','title':'Food room',
                    'text':'Food '+('x'*29999),'origin':'synthetic fixture'} for i in range(3)]
                save(a,state)
                bounded=await session.call_tool('search_game_references',{'query':'food','category':'room','limit':10})
                assert not bounded.is_error
                payload=next(c.text for c in bounded.content if c.type=='text')
                assert len(payload.encode())<=65536
                result=json.loads(payload)
                assert result['total_matches']==3 and result['results_truncated']
                assert len(result['results'])==2 and all(len(r['text'])==30004 for r in result['results'])

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


def test_field_discovery_returns_meanings_without_state_values(setup):
    advisor,state=setup
    state['domains']['research']={'coverage':'partial','reason':'synthetic research fixture',
        'data':{'technologies':[], 'field_definitions':{'requirements':{
            'definition':'Expanded prerequisites, not a full unlock decision',
            'source':'test-only source anchor'}}}}
    save(advisor,state)
    result=advisor.describe('research')
    assert result['field_definitions']==state['domains']['research']['data']['field_definitions']
    assert 'technologies' not in result['field_definitions']
    assert advisor.describe('resources')['field_definitions']=={}


def test_field_meanings_obey_response_budget(setup):
    advisor,state=setup
    state['domains']['resources']['data']['field_definitions']={'huge':'x'*65536}
    save(advisor,state)
    with pytest.raises(ValueError,match='64 KiB'):
        advisor.describe('resources')


def test_guidance_relevance_before_authority_and_whole_tokens(setup):
    advisor,_=setup
    def record(id,title,text,authority='community',versions=None):
        return {'id':id,'title':title,'text':text,'authority':authority,'kind':'guide',
            'url':'https://example.com/'+id,'retrieved_at':'2026-01-01T00:00:00Z',
            'game_versions':versions or []}
    sources=[record('official','Official announcement','Food and unrelated changes.','official'),
             record('relevant','Food storage spoilage','Food storage spoilage in warehouses.'),
             record('substring','Unrelated','There is more text here.')]
    advisor.corpus_path.write_text(json.dumps(sources))
    result=advisor.search('How can I reduce food storage spoilage?','0.71.44')
    assert result['results'][0]['id']=='relevant'
    assert result['results'][0]['matched_terms']==['food','spoilage','storage']
    assert not advisor.search('ore')['results']
    assert not advisor.search('how can I')['results']
    assert advisor.search('food',authority='official')['results'][0]['id']=='official'


def test_guidance_version_then_authority_breaks_relevance_ties(setup):
    advisor,_=setup
    sources=[]
    for id,authority,versions in [('old','official',['0.60']),('community','community',['0.71']),
                                   ('developer','developer',['0.71']),('exact','community',['0.71.44'])]:
        sources.append({'id':id,'title':'Food','text':'Food','authority':authority,'kind':'guide',
            'url':'https://example.com/'+id,'retrieved_at':'2026-01-01T00:00:00Z','game_versions':versions})
    advisor.corpus_path.write_text(json.dumps(sources))
    result=advisor.search('food','0.71.44')
    assert [s['id'] for s in result['results']]==['exact','developer','community','old']
    assert result['results'][-1]['version_compatibility']=='mismatch'


def test_guidance_response_budget_preserves_complete_citations(setup):
    advisor,_=setup
    sources=[{'id':str(i),'title':'Food','text':'Food '+('x'*11990),'kind':'guide',
        'url':'https://example.com/'+str(i),'retrieved_at':'2026-01-01T00:00:00Z'} for i in range(10)]
    advisor.corpus_path.write_text(json.dumps(sources))
    result=advisor.search('food',limit=10)
    assert result['total_matches']==10 and result['results_truncated']
    assert 0<len(result['results'])<10 and len(json.dumps(result).encode())<=65536
    assert all(s['url']=='https://example.com/'+s['id'] and len(s['text'])==11995 for s in result['results'])


def test_direct_nested_unavailable_page_is_unknown_not_empty(setup):
    advisor,state=setup
    state['domains']['trade']={'coverage':'partial','reason':'mixed domain','data':{
        'pipeline':{'coverage':'unavailable','scope':'city','reason':'Battlefield','rows':[]}}}
    advisor.snapshot_path.write_text(json.dumps(state))
    result=advisor.query('trade','/pipeline/rows')
    assert result['coverage']=='unavailable' and result['data'] is None and result['total'] is None
    assert result['subtree_scope']=='city' and result['coverage_reason']=='Battlefield'
    assert advisor.query('trade','/pipeline/coverage')['data']=='unavailable'
    state['domains']['trade']['data']['pipeline']['coverage']='partial'
    advisor.snapshot_path.write_text(json.dumps(state))
    result=advisor.query('trade','/pipeline/rows')
    assert result['coverage']=='partial' and result['data']==[] and result['total']==0


def test_paged_read_keeps_collection_limits_failures_and_truncation(setup):
    a,s=setup
    s['domains']['services']={'coverage':'partial','reason':'synthetic','data':{
        'access_policy':{'coverage':'partial','truncated':True,'failed_service_types':1,
            'rule_row_limit':10000,'cohort_rules':[{'id':i} for i in range(3)]}}}
    save(a,s)
    first=a.query('services','/access_policy/cohort_rules',limit=2)
    second=a.query('services','/access_policy/cohort_rules',offset=2,limit=2)
    expected=[{'path':'/access_policy','truncated':True,'failed_service_types':1,'rule_row_limit':10000}]
    assert first['total']==second['total']==3
    assert first['collection_diagnostics']==second['collection_diagnostics']==expected
    assert first['next_offset']==2 and second['next_offset'] is None
