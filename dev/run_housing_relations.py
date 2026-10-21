"""Unshipped detached housing field/relationship view and real MCP join/cap checks over same-callback native data."""
import argparse,json,sys,os,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from game_fixture_lock import exclusive_fixture
from run_stockpile_probe import run,sha
from run_player_chat_check import native_environment
from housing_query_view import build_view,MAX_RELATIONS

SOURCES=['dev/housing_query_view.py','test_housing_query_view.py','dev/run_housing_relations.py',
 'housing-relations-candidate-example.json','dev/candidates/housing/query/StockpileScenario.java',
 'dev/candidates/housing/syx/assistant/candidate/HousingObservation.java','dev/run_stockpile_probe.py',
 'mod/tests/LiveSmoke.java','dev/native_game_completion.py','syx_query.py','syx_mcp.py']

async def verify(state,manifest):
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    from syx_mcp import Snapshot
    fixture=json.loads((state/'stockpile-fixture.json').read_text());assert fixture['passed'] and fixture['same_callback']
    original=state/'housing-query-observation.json';snapshot=Snapshot.model_validate_json(original.read_bytes())
    assert snapshot.game_version=='0.71.44' and snapshot.domains['housing'].data['physical_home_candidate']==fixture['candidate']
    candidate=fixture['candidate'];rooms=candidate['data']['rooms'];assert len(rooms)>1
    began=time.perf_counter_ns();view=build_view(candidate);elapsed=time.perf_counter_ns()-began
    expected_links=[{'room_id':r['room_id'],'resident_id':rid,'roster_index':i} for r in rooms for i,rid in enumerate(r['occupant_roster']['ids'])]
    assert view['home_assignments']['data']['rows']==expected_links and expected_links
    first_count=len(rooms[0]['occupant_roster']['ids']);assert 0<first_count<len(expected_links)
    limited=build_view(candidate,first_count)['home_assignments'];assert limited['data']['truncated']
    assert len(limited['data']['rows'])==first_count and all(r['room_id']==rooms[0]['room_id'] for r in limited['data']['rows'])
    payload=snapshot.model_dump(mode='json');data=payload['domains']['housing']['data']
    assert not any(k in data for k in ['home_records','home_assignments','capped_home_assignments'])
    data.update(view);data['capped_home_assignments']=limited
    augmented=Snapshot.model_validate(payload)
    assert augmented.snapshot_id==snapshot.snapshot_id and augmented.tick==snapshot.tick and augmented.captured_at==snapshot.captured_at
    assert augmented.ui_context==snapshot.ui_context and augmented.scene==snapshot.scene
    retained=state/'retained-housing-relations';retained.mkdir(mode=0o700)
    (retained/'snapshot.json').write_text(augmented.model_dump_json())
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
        spec=json.loads((ROOT/'housing-relations-candidate-example.json').read_text());spec['expected_snapshot_id']=snapshot.snapshot_id
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
        cap_spec={'queries':[{'source':{'domain':'housing','path':'/capped_home_assignments/data/rows'},'aggregates':{'n':{'op':'count'}}}],'expected_snapshot_id':snapshot.snapshot_id}
        response,cap=await call('select_game_state',{'spec':cap_spec});assert not response.is_error
        assert cap['results'][0]['rows']==[{'n':first_count}]
        cd=next(x for x in cap['results'][0]['sources'][0]['collection_diagnostics'] if x['path']=='/capped_home_assignments/data')
        assert cd['truncated'] is True and cd['row_limit']==first_count and cd['room_scan_complete'] is True
        response,refusal=await call('select_game_state',{'spec':{**spec,'expected_snapshot_id':'different-housing-observation'}})
        assert response.is_error and 'Snapshot changed' in refusal
    return {'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),
      'scope':'Developer-only detached field/relationship view derived from same-callback native candidate data and checked through unchanged real MCP; no production housing mapping.',
      'native_home_rows':len(rooms),'derived_assignment_rows':len(expected_links),'grouped_occupied_home_rows':len(expected_counts),'actual_mcp_calls':calls,
      'authored_example_join_group_filter_projection_parity':True,'field_meanings_discoverable':True,'both_source_diagnostics_preserved':True,
      'same_original_observation_ui_scene_and_pin':True,'stale_pin_refused':True,'relation_cap_atomic_home_batch':True,'relation_cap_room_scan_can_still_be_complete':True,
      'native_relation_row_limit_case':first_count,'detached_view_bytes':len(json.dumps(view,allow_nan=False).encode()),'detached_build_elapsed_ns':elapsed,
      'candidate_packaged_in_player':False,'production_integration_ready':False,'provider_calls':0,'save_writes':0,
      'mod_jar_sha256':manifest['mod_jar_sha256'],'production_source_sha256':manifest['validation']['production_source_sha256'],'python_source_sha256':manifest['validation']['python_source_sha256'],
      'housing_static_review_sha256':sha(ROOT/'HOUSING_BOUNDARY_REVIEW.json'),'source_sha256':{n:sha(ROOT/n) for n in SOURCES},'private_native_snapshot_sha256':sha(original),
      'limits':['The Java fixture appends only detached candidate DTOs to its own same-callback production snapshot. The off-game-thread Python adapter deterministically adds home/relationship tables and field descriptions to a private retained copy, preserving original identifiers/context; this is developer augmentation, not a shipped collector or supported player query.',
        'All relationships come from recorded/resolved roster IDs in that one observation. No additional entity request, physical presence, stable identity, selected room, effective vacancy/eligibility or cached-entity-prefix completeness is inferred. Roster multiplicity/order is preserved, not deduplicated into a census.',
        'One paused ordinary-home city and one real smaller relationship bound; no native chamber/fault/unavailable relationship view, maximum 10000-row/2MiB/64-ID branch or large-city/FPS acceptance. Synthetic cases are separate.',
        'The single detached build interval includes validation/deep-copy/JSON byte checking outside the game thread. It is not a performance benchmark, game-frame interval or maximum-work acceptance.',
        'Field meanings inherit the fixed source-verified 0.71.44 readers and prior semantic review, not separate official stable API contracts or a new external guidance review. Production API-support inventory/player wiring/provider guidance and release gates remain open.']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['game-dir','jdk-home','java','save']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--candidate-dir',type=Path);p.add_argument('--validation',type=Path)
    a=p.parse_args();review=json.loads((ROOT/'HOUSING_BOUNDARY_REVIEW.json').read_text());assert review['passed']
    for n,h in review['source_sha256'].items():assert sha(ROOT/n)==h
    for n in SOURCES:assert (ROOT/n).is_file(),n
    assert sha(a.game_dir/'SongsOfSyx.jar')==review['game_jar_sha256'] and sha(a.game_dir/'info/SongsOfSyx-sources.jar')==review['source_archive_sha256']
    with exclusive_fixture():
        run(a,scenario_override=ROOT/'dev/candidates/housing/query/StockpileScenario.java',
          extra_sources=[ROOT/'dev/candidates/housing/syx/assistant/candidate/HousingObservation.java'],verifier=verify,
          report_name='housing-relations-validation.json',boundary_review_path=ROOT/'HOUSING_BOUNDARY_REVIEW.json',
          completion_marker=('housing-query-clean-exit.json',{'passed':True,'same_callback':True}))
