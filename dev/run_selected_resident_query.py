"""Existing production selected-person/home/staffing three-join query through actual MCP in a copied city; no new game mapping."""
import argparse,json,os,sys,hashlib,zipfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from game_fixture_lock import exclusive_fixture
from run_stockpile_probe import run,sha
from run_player_chat_check import native_environment
SOURCES=['dev/run_selected_resident_query.py','dev/candidates/housing/selected-resident/StockpileScenario.java',
 'selected-resident-query-example.json','test_selected_resident_query.py','mod/src/main/java/syx/assistant/StateCollector.java',
 'mod/src/main/java/syx/assistant/HousingObservation.java','dev/run_stockpile_probe.py','mod/tests/LiveSmoke.java','dev/native_game_completion.py','syx_housing.py','syx_query.py','syx_mcp.py']
GAME_SOURCES=['settlement/stats/colls/StatsHome.java','settlement/stats/colls/StatsWork.java','settlement/room/home/HOME.java',
 'settlement/room/home/house/HomeInstance.java','settlement/room/main/employment/RoomEmploymentIns.java']

async def verify(state,manifest):
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    from syx_mcp import Snapshot
    fixture=json.loads((state/'stockpile-fixture.json').read_text());assert fixture['passed'] and fixture['same_callback']
    entries=fixture['samples'];assert len(entries)==2 and len({e['entity_id'] for e in entries})==2
    snapshots=[Snapshot.model_validate_json((state/e['file']).read_bytes()) for e in entries]
    assert len({s.session_id for s in snapshots})==1 and len({s.snapshot_id for s in snapshots})==2 and len({s.tick for s in snapshots})==1
    expected=[]
    for e,s in zip(entries,snapshots):
        subject=s.domains['entities'].data['selected_subject'];assert subject['entity_id']==e['entity_id']
        assert s.ui_context['selected_subject']['entity_id']==e['entity_id']
        jobs=[r for r in s.domains['employment'].data['rooms'] if r['room_id']==e['workplace_room_id']];assert len(jobs)==1
        job=jobs[0];assert job['blueprint_id']==e['workplace_blueprint_id']
        for name in ['employed','needed','target','capacity']:assert job[name]==e['workplace_'+name]
        assert subject['relationships']['home_assignment']=={'available':True,'data':{'tile_x':e['home_x'],'tile_y':e['home_y']}}
        expected.append({'entity_id':e['entity_id'],'recorded_home_room_id':e['home_room_id'],'home_kind':e['home_kind'],
          'home_service_tile_x':e['home_x'],'home_service_tile_y':e['home_y'],'configured_home_capacity':e['home_capacity'],
          'person_recorded_home_tile':{'tile_x':e['home_x'],'tile_y':e['home_y']},'recorded_workplace_room_id':e['workplace_room_id'],'observed_workplace':job})
    retained=state/'retained-selected-residents';retained.mkdir(mode=0o700)
    env={**native_environment(os.environ),'SYX_STATE_DIR':str(retained)}
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(ROOT),env=env)
    spec=json.loads((ROOT/'selected-resident-query-example.json').read_text());calls=0
    async with stdio_client(params) as streams:
      async with ClientSession(*streams) as session:
        await session.initialize()
        async def call(name,args,error=False):
            nonlocal calls
            r=await session.call_tool(name,args);calls+=1
            text=next(c.text for c in r.content if c.type=='text');assert len(text.encode())<=65536 and r.is_error==error,text
            return text if error else json.loads(text)
        for i,(e,s) in enumerate(zip(entries,snapshots)):
            pending=retained/'snapshot.pending';pending.write_bytes((state/e['file']).read_bytes());pending.replace(retained/'snapshot.json')
            if i:
                refused=await call('select_game_state',{'spec':{**spec,'expected_snapshot_id':snapshots[0].snapshot_id}},True);assert 'Snapshot changed' in refused
            selected=await call('select_game_state',{'spec':{**spec,'expected_snapshot_id':s.snapshot_id}})
            assert selected['results'][0]['rows']==[expected[i]] and selected['results'][0]['matched_total']==1
            assert selected['state']['snapshot_id']==s.snapshot_id and selected['ui_context']==s.ui_context
            sources=selected['results'][0]['sources'];assert len(sources)==4 and [x['domain'] for x in sources]==['entities','housing','housing','employment']
            assert any(x.get('room_scan_complete') is True for x in sources[1]['collection_diagnostics'])
            assert any(x.get('failed_room_reads')==0 for x in sources[2]['collection_diagnostics'])
            raw=await call('query_game_state',{'domain':'entities','pointer':'/selected_subject/relationships/home_assignment','expected_snapshot_id':s.snapshot_id})
            assert raw['data']=={'available':True,'data':{'tile_x':e['home_x'],'tile_y':e['home_y']}}
        required_paths={
          'entities':{'/selected_subject/entity_id','/selected_subject/relationships/home_assignment/data/tile_x','/selected_subject/relationships/workplace/data/room_id'},
          'housing':{'/home_records/data/rooms/*/room_id','/home_records/data/rooms/*/service_tile_x','/home_assignments/data/rows/*/resident_id'},
          'employment':{'/rooms/*/room_id','/rooms/*/employed'}}
        for domain,required in required_paths.items():
            description=await call('describe_game_fields',{'domain':domain})
            assert required<={field['path'] for field in description['fields']},domain
    return {'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),
      'scope':'Authored selected housed-worker three-join query over existing production exports; two underlying subject selections, public direct-getter checks and unmodified retained-original MCP observations.',
      'selected_housed_workers':2,'actual_mcp_calls':calls,'query_sources_per_result':4,'query_joins':3,'observed_query_field_paths_discovered':8,
      'same_callback_selected_home_staffing_parity':True,'same_original_snapshot_and_ui':True,'new_selection_observation_rejects_previous_snapshot_pin':True,
      'provider_calls':0,'explicit_fixture_save_requests':0,'production_payload_unchanged':True,
      'mod_jar_sha256':manifest['mod_jar_sha256'],'production_source_sha256':manifest['validation']['production_source_sha256'],'python_source_sha256':manifest['validation']['python_source_sha256'],
      'source_sha256':{n:sha(ROOT/n) for n in SOURCES},'selected_game_source_sha256':GAME_SOURCE_HASHES,
      'private_observation_sha256':[sha(state/e['file']) for e in entries],
      'public_test_only_actions':['VIEW.s.activate','GAME.SPEED.speedSet(0)','VIEW.s.ui.subjects.showSingle for two existing naturally housed employed subjects'],
      'limits':['Two selected housed workers in one paused copied-city callback, not a citywide census, live commuting study, natural reassignment, all scenes, every resident or large-city query-cost acceptance.',
        'This example requires an available selected subject with a recorded workplace and available housing tables. Inner home joins can have zero matches under prefix/failure bounds; missing rows are not proof of homelessness. Missing cached employment stays null with its source diagnostics, not proof of no workplace.',
        'Recorded home coordinates are service/assignment tiles and workplace coordinates are stored room anchors. No physical presence, reachability, search radius, distance/commute time or effective vacancy is inferred.',
        'Underlying public subject selection may be hidden/obscured. Own public test UI selection is not physical input/visibility or additional UI-context API acceptance.',
        'A selection change alone does not rotate a snapshot pin. Refusal is tested only after publishing the new selected-subject observation; no immediate live-selection invalidation or UI responsiveness guarantee.','Original observations are served privately after collection through one MCP process. This is not concurrent live query servicing or a transaction across different game callbacks. No normal profile/save, game action, new getter/tool or source-matched player rebuild is implied.']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['game-dir','jdk-home','java','save']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--candidate-dir',type=Path);p.add_argument('--validation',type=Path)
    a=p.parse_args();review=json.loads((ROOT/'HOUSING_CONTRACT_REVIEW.json').read_text());assert review['passed']
    for n,h in review['source_sha256'].items():assert sha(ROOT/n)==h,n
    assert sha(a.game_dir/'SongsOfSyx.jar')==review['game_jar_sha256'] and sha(a.game_dir/'info/SongsOfSyx-sources.jar')==review['source_archive_sha256']
    with zipfile.ZipFile(a.game_dir/'info/SongsOfSyx-sources.jar') as z:GAME_SOURCE_HASHES={n:hashlib.sha256(z.read(n)).hexdigest() for n in GAME_SOURCES}
    with exclusive_fixture():
        run(a,scenario_override=ROOT/'dev/candidates/housing/selected-resident/StockpileScenario.java',extra_sources=[],verifier=verify,
          report_name='selected-resident-query-validation.json',boundary_review_path=ROOT/'HOUSING_CONTRACT_REVIEW.json',
          completion_marker=('selected-resident-clean-exit.json',{'passed':True,'samples':2}))
