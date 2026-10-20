"""Developer-augmented native housing through real MCP; verify fixed scalar diagnostic propagation."""
import argparse,json,sys,shutil
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from game_fixture_lock import exclusive_fixture
from run_stockpile_probe import run,sha
from run_player_chat_check import native_environment
import os

SOURCES=['dev/candidates/housing/query/StockpileScenario.java','dev/candidates/housing/syx/assistant/candidate/HousingObservation.java',
 'dev/run_housing_query_diagnostics.py','housing-query-candidate-example.json','dev/run_stockpile_probe.py','mod/tests/LiveSmoke.java','dev/native_game_completion.py','syx_query.py','syx_mcp.py']

async def verify(state,manifest):
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    from syx_mcp import Snapshot
    fixture=json.loads((state/'stockpile-fixture.json').read_text());assert fixture['passed'] and fixture['same_callback']
    original=state/'housing-query-observation.json';snapshot=Snapshot.model_validate_json(original.read_bytes())
    full=fixture['candidate'];data=full['data'];rows=data['rooms'];assert rows and data['room_scan_complete']
    assert snapshot.domains['housing'].data['physical_home_candidate']==full
    assert fixture['capped']['data']['room_scan_complete'] is False and len(fixture['capped']['data']['rooms'])==1
    retained=state/'retained-housing-candidate';retained.mkdir(mode=0o700);shutil.copy2(original,retained/'snapshot.json')
    env=native_environment(os.environ);env['SYX_STATE_DIR']=str(retained)
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(ROOT),env=env)
    calls=0
    async with stdio_client(params) as streams:
      async with ClientSession(*streams) as session:
        await session.initialize()
        async def call(name,args):
            nonlocal calls
            response=await session.call_tool(name,args);calls+=1
            body=next(c.text for c in response.content if c.type=='text');assert len(body.encode())<=65536
            return response,json.loads(body) if not response.is_error else body
        response,desc=await call('describe_game_fields',{'domain':'housing'});assert not response.is_error
        assert '/physical_home_candidate/data/rooms' in json.dumps(desc) and '/occupants_reported' in json.dumps(desc)
        spec=json.loads((ROOT/'housing-query-candidate-example.json').read_text());spec['expected_snapshot_id']=snapshot.snapshot_id
        response,result=await call('select_game_state',{'spec':spec});assert not response.is_error,result
        expected=[]
        for kind in sorted({r['kind'] for r in rows}):
            subset=[r for r in rows if r['kind']==kind]
            expected.append({'kind':kind,'observed_homes':len(subset),'reported_assignments':sum(r['occupants_reported'] for r in subset),'configured_capacity_sum':sum(r['capacity_configured'] for r in subset)})
        assert sorted(result['results'][0]['rows'],key=lambda r:r['kind'])==expected
        projected=[{'room_id':r['room_id'],'kind':r['kind'],'assigned':r['occupants_reported'],'capacity':r['capacity_configured']} for r in rows if r['occupants_reported']>0]
        projected.sort(key=lambda r:(-r['assigned'],r['room_id']))
        assert result['results'][1]['rows']==projected[:5] and result['results'][1]['matched_total']==len(projected)
        assert result['state']['session_id']==snapshot.session_id and result['ui_context']==snapshot.ui_context
        for r in result['results']:
            assert r['sources'][0]['subtree_coverage']=='partial' and r['sources'][0]['subtree_scope']=='instantiated_city_home_records'
        response,raw=await call('query_game_state',{'domain':'housing','pointer':'/physical_home_candidate/data','expected_snapshot_id':snapshot.snapshot_id});assert not response.is_error
        assert raw['data']==data
        capped_spec={'queries':[{'source':{'domain':'housing','path':'/capped_home_candidate/data/rooms'},'aggregates':{'n':{'op':'count'}}}],'expected_snapshot_id':snapshot.snapshot_id}
        response,capped=await call('select_game_state',{'spec':capped_spec});assert not response.is_error
        assert capped['results'][0]['rows']==[{'n':1}]
        diagnostics=capped['results'][0]['sources'][0]['collection_diagnostics']
        present=set().union(*(set(x) for x in diagnostics)) if diagnostics else set()
        missing=sorted({'room_slots_scanned','room_map_size','scan_limit','room_scan_complete','failed_room_reads','failed_rosters','truncated_rosters'}-present)
        assert missing==[] and 'row_limit' in present
        actual=next(d for d in diagnostics if d['path']=='/capped_home_candidate/data')
        for key in ['room_slots_scanned','room_map_size','scan_limit','room_scan_complete','failed_room_reads','failed_rosters','truncated_rosters','row_limit']:
            assert actual[key]==fixture['capped']['data'][key],key
        assert actual['room_scan_complete'] is False
        bad={**spec,'expected_snapshot_id':'different-candidate-observation'}
        response,refusal=await call('select_game_state',{'spec':bad});assert response.is_error and 'Snapshot changed' in refusal
    return {'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),
      'scope':'Developer-augmented same-callback native snapshot through unmodified real MCP; positive query semantics and repaired diagnostic propagation, not production housing mapping acceptance.',
      'native_home_rows':len(rows),'native_recorded_residents':sum(r['occupants_reported'] for r in rows),'actual_mcp_calls':calls,
      'grouped_sums_filter_projection_order_parity':True,'original_snapshot_ui_context_and_pin':True,'stale_pin_refused':True,
      'raw_diagnostics_preserved':True,'select_diagnostics_complete':True,'native_capped_diagnostics_parity':True,'missing_select_diagnostic_keys':missing,
      'production_integration_ready':False,'diagnostic_repair_ready':True,'candidate_packaged_in_player':False,'provider_calls':0,'save_writes':0,
      'mod_jar_sha256':manifest['mod_jar_sha256'],'production_source_sha256':manifest['validation']['production_source_sha256'],
      'python_source_sha256':manifest['validation']['python_source_sha256'],
      'housing_static_review_sha256':sha(ROOT/'HOUSING_BOUNDARY_REVIEW.json'),'source_sha256':{n:sha(ROOT/n) for n in SOURCES},'private_native_snapshot_sha256':sha(original),
      'limits':['The Java fixture appends unchanged candidate DTOs to its own detached current production snapshot in the same callback; this is a developer-only augmentation, not a shipped collector field or existing production housing MCP support.',
        'Observed shape discovery is not authoritative field-meaning/source-contract discovery. Authored candidate paths/example are provisional; no new field definitions or API-support entry is claimed.',
        'Actual selective source metadata now retains partial/scope, row_limit and all seven fixed housing-specific scan/error/truncation keys. The native one-row capped count explicitly carries room_scan_complete=false.',
        'Raw data queries also preserve the explicit diagnostics; selective metadata no longer requires fetching the entire raw observation. No generic arbitrary invocation, game mutation, UI selection or permanent room identity is added.',
        'One paused copied city, not chamber-specific queries, native fault-query paths, broader lifecycle, cache-cap/large-city or provider guidance acceptance. Earlier native chamber/scene/fault evidence remains separate.']}

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
          report_name='housing-query-diagnostics-validation.json',boundary_review_path=ROOT/'HOUSING_BOUNDARY_REVIEW.json',
          completion_marker=('housing-query-clean-exit.json',{'passed':True,'same_callback':True}))
