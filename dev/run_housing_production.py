"""Production housing getter/DTO/retained-original MCP relationship checks; no developer snapshot augmentation."""
import argparse,json,sys,os,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from game_fixture_lock import exclusive_fixture
from run_stockpile_probe import run,sha
from run_player_chat_check import native_environment
from syx_housing import build_view,MAX_RELATIONS

SOURCES=['syx_housing.py','test_housing_query_view.py','test_syx_housing.py','dev/run_housing_production.py',
 'housing-query-example.json','dev/candidates/housing/production/StockpileScenario.java',
 'dev/candidates/housing/syx/assistant/candidate/HousingObservation.java','dev/run_stockpile_probe.py',
 'mod/tests/LiveSmoke.java','dev/native_game_completion.py','syx_query.py','syx_mcp.py']

async def verify(state,manifest):
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    from syx_mcp import Snapshot
    fixture=json.loads((state/'stockpile-fixture.json').read_text());assert fixture['passed'] and fixture['same_callback']
    original=state/'housing-query-observation.json';snapshot=Snapshot.model_validate_json(original.read_bytes())
    assert snapshot.game_version=='0.71.44' and snapshot.domains['housing'].data['home_records']==fixture['candidate']
    candidate=fixture['candidate'];rooms=candidate['data']['rooms'];assert len(rooms)>1
    began=time.perf_counter_ns();view=build_view(candidate);elapsed=time.perf_counter_ns()-began
    expected_links=[{'room_id':r['room_id'],'resident_id':rid,'roster_index':i} for r in rooms for i,rid in enumerate(r['occupant_roster']['ids'])]
    assert view['home_assignments']['data']['rows']==expected_links and expected_links
    retained=state/'retained-housing-production';retained.mkdir(mode=0o700)
    (retained/'snapshot.json').write_bytes(original.read_bytes())
    env=native_environment(os.environ);env['SYX_STATE_DIR']=str(retained)
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(ROOT),env=env)
    calls=0
    async with stdio_client(params) as streams:
      async with ClientSession(*streams) as session:
        await session.initialize()
        async def call(name,args):
            nonlocal calls
            response=await session.call_tool(name,args);calls+=1
            text=next(c.text for c in response.content if c.type=='text');assert len(text.encode())<=65536
            return response,json.loads(text) if not response.is_error else text
        response,desc=await call('describe_game_fields',{'domain':'housing'});assert not response.is_error
        assert desc['field_definitions']==view['field_definitions']
        assert 'not separately documented stable' in desc['field_definitions']['home_records']['contract']
        spec=json.loads((ROOT/'housing-query-example.json').read_text());spec['expected_snapshot_id']=snapshot.snapshot_id
        response,result=await call('select_game_state',{'spec':spec});assert not response.is_error,result
        expected_counts=sorted([{'room_id':r['room_id'],'kind':r['kind'],'reported_occupants':r['occupants_reported'],'observed_roster_links':len(r['occupant_roster']['ids'])} for r in rooms if r['occupant_roster']['ids']],key=lambda r:r['room_id'])
        assert result['results'][0]['rows']==expected_counts and result['results'][0]['matched_total']==len(expected_counts)
        expected_first=sorted([{'room_id':r['room_id'],'resident_id':r['occupant_roster']['ids'][0],'roster_index':0,'configured_capacity':r['capacity_configured']} for r in rooms if r['kind']=='ordinary_home' and r['occupant_roster']['ids']],key=lambda r:r['room_id'])
        assert result['results'][1]['rows']==expected_first[:5] and result['results'][1]['matched_total']==len(expected_first)
        assert result['state']['session_id']==snapshot.session_id and result['ui_context']==snapshot.ui_context
        for r in result['results']:
            assert len(r['sources'])==2
            rel=r['sources'][0];home=r['sources'][1]
            assert rel['subtree_scope']=='instantiated_city_recorded_home_assignments' and home['subtree_scope']=='instantiated_city_home_records'
            rd=next(x for x in rel['collection_diagnostics'] if x['path']=='/home_assignments/data')
            hd=next(x for x in home['collection_diagnostics'] if x['path']=='/home_records/data')
            assert rd['truncated'] is False and rd['row_limit']==MAX_RELATIONS and hd['row_limit']==1000
        response,raw=await call('query_game_state',{'domain':'housing','pointer':'/home_assignments/data','expected_snapshot_id':snapshot.snapshot_id});assert not response.is_error
        assert raw['data']==view['home_assignments']['data']
        response,support=await call('get_game_api_support',{'query':'city_home_records'})
        assert not response.is_error and support['capabilities'][0]['id']=='city_home_records'
        assert support['capabilities'][0]['support']=='public_source_verified'
        response,refusal=await call('select_game_state',{'spec':{**spec,'expected_snapshot_id':'different-housing-observation'}})
        assert response.is_error and 'Snapshot changed' in refusal
    return {'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),
      'scope':'Production home getter/DTO equality and unmodified retained-original MCP field meanings/relationships in the same original observation; no developer snapshot augmentation.',
      'native_home_rows':len(rooms),'derived_assignment_rows':len(expected_links),'grouped_occupied_home_rows':len(expected_counts),'actual_mcp_calls':calls,
      'authored_example_join_group_filter_projection_parity':True,'field_meanings_discoverable':True,'both_source_diagnostics_preserved':True,
      'same_original_observation_ui_scene_and_pin':True,'stale_pin_refused':True,'public_support_entry_discoverable':True,
      'detached_view_bytes':len(json.dumps(view,allow_nan=False).encode()),'detached_build_elapsed_ns':elapsed,
      'production_housing_mapping':True,'provider_calls':0,'save_writes':0,
      'mod_jar_sha256':manifest['mod_jar_sha256'],'production_source_sha256':manifest['validation']['production_source_sha256'],'python_source_sha256':manifest['validation']['python_source_sha256'],
      'housing_static_review_sha256':sha(ROOT/'HOUSING_BOUNDARY_REVIEW.json'),'source_sha256':{n:sha(ROOT/n) for n in SOURCES},'private_native_snapshot_sha256':sha(original),
      'limits':['The actual production Java collector supplies home_records. The production MCP cache derives relationships/definitions once per newly decoded observation outside the game thread; no fabricated snapshot fields or game reads are added by the verifier.',
        'Fixed original candidate and production readers share the reviewed public getter routes; equality is implementation parity, not an independent raw-storage audit. Earlier native direct-getter/chamber/scene/fault reports keep their original source scopes.',
        'One paused copied city with ordinary homes: not native occupied-chamber/fault/unavailable relationship acceptance, actual maximum relation/byte/roster bounds, broad lifecycle, natural reassignment or large-city/FPS acceptance.',
        'Relationships preserve recorded/resolved ID multiplicity/order, not physical presence, permanent identity, effective vacancy/eligibility, UI selection or complete cached entity membership. Cohort ledgers are weighted, not unique beds.',
        'Detached build timing is descriptive and outside the game thread. Final exact-source source-contract, scene/fault/chamber/cost/discovery/provider/release gates are recorded separately.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['game-dir','jdk-home','java','save']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--candidate-dir',type=Path);p.add_argument('--validation',type=Path)
    a=p.parse_args();review=json.loads((ROOT/'HOUSING_BOUNDARY_REVIEW.json').read_text());assert review['passed']
    for n,h in review['source_sha256'].items():assert sha(ROOT/n)==h
    for n in SOURCES:assert (ROOT/n).is_file(),n
    assert sha(a.game_dir/'SongsOfSyx.jar')==review['game_jar_sha256'] and sha(a.game_dir/'info/SongsOfSyx-sources.jar')==review['source_archive_sha256']
    with exclusive_fixture():
        run(a,scenario_override=ROOT/'dev/candidates/housing/production/StockpileScenario.java',
          extra_sources=[ROOT/'dev/candidates/housing/syx/assistant/candidate/HousingObservation.java'],verifier=verify,
          report_name='housing-production-validation.json',boundary_review_path=ROOT/'HOUSING_BOUNDARY_REVIEW.json',
          completion_marker=('housing-query-clean-exit.json',{'passed':True,'same_callback':True}))
