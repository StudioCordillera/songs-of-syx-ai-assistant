"""Six production housing observations during finite unpaused copied-city simulation; actual retained-original MCP cache transitions."""
import argparse,hashlib,json,os,sys,zipfile
from datetime import datetime,timezone
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from game_fixture_lock import exclusive_fixture
from run_stockpile_probe import run,sha
from run_player_chat_check import native_environment
SOURCES=['dev/run_housing_running.py','dev/candidates/housing/running/StockpileScenario.java',
 'mod/src/main/java/syx/assistant/HousingObservation.java','dev/run_stockpile_probe.py','mod/tests/LiveSmoke.java',
 'dev/native_game_completion.py','syx_housing.py','syx_mcp.py','syx_query.py']
GAME_SOURCES=['game/GAME.java','game/GameSpeed.java','game/time/TIME.java','settlement/room/home/HOME.java',
 'settlement/room/home/house/HomeInstance.java','settlement/room/home/chamber/ChamberInstance.java']

async def verify(state,manifest):
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    from syx_mcp import Snapshot
    fixture=json.loads((state/'stockpile-fixture.json').read_text());assert fixture['passed'] and fixture['sample_count']==6 and fixture['simulation_speed_during_sampling']==1
    samples=fixture['samples'];snapshots=[];expected=[]
    for entry in samples:
        assert entry['same_callback_direct_parity']
        path=state/entry['file'];snapshot=Snapshot.model_validate_json(path.read_bytes());snapshots.append(snapshot)
        records=snapshot.domains['housing'].data['home_records']['data'];rooms=records['rooms']
        links=[{'room_id':r['room_id'],'resident_id':rid,'roster_index':i} for r in rooms for i,rid in enumerate(r['occupant_roster']['ids'])]
        assert len(rooms)==entry['home_rows'] and len(links)==entry['roster_links'] and snapshot.tick==entry['tick']
        expected.append(links)
    ticks=[s.tick for s in snapshots];assert all(b>a for a,b in zip(ticks,ticks[1:]))
    seconds=[e['game_seconds'] for e in samples];assert all(b>a for a,b in zip(seconds,seconds[1:]))
    assert len({s.snapshot_id for s in snapshots})==6 and len({s.session_id for s in snapshots})==1
    pair_multisets=[Counter((link['room_id'],link['resident_id']) for link in links) for links in expected]
    retained=state/'retained-running-observations';retained.mkdir(mode=0o700)
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(ROOT),env={**native_environment(os.environ),'SYX_STATE_DIR':str(retained)})
    calls=0
    def publish(index):
        # A private retained-observation mailbox, never the running mod's live mailbox.
        pending=retained/'snapshot.pending';pending.write_bytes((state/samples[index]['file']).read_bytes());pending.replace(retained/'snapshot.json')
    async with stdio_client(params) as streams:
      async with ClientSession(*streams) as session:
        await session.initialize()
        async def call(name,args,error=False):
            nonlocal calls
            response=await session.call_tool(name,args);calls+=1
            text=next(c.text for c in response.content if c.type=='text');assert len(text.encode())<=65536
            assert response.is_error==error,text
            return text if error else json.loads(text)
        for i,snapshot in enumerate(snapshots):
            publish(i)
            if i:
                refusal=await call('select_game_state',{'spec':{'queries':[{'source':{'domain':'housing','path':'/home_assignments/data/rows'},'aggregates':{'n':{'op':'count'}}}],'expected_snapshot_id':snapshots[i-1].snapshot_id}},error=True)
                assert 'Snapshot changed' in refusal
            actual=await call('query_game_state',{'domain':'housing','pointer':'/home_assignments/data','expected_snapshot_id':snapshot.snapshot_id})
            assert actual['data']['rows']==expected[i]
            assert actual['data']['room_scan_complete'] and not actual['data']['truncated'] and actual['data']['failed_room_reads']==actual['data']['failed_rosters']==0
            query={'source':{'domain':'housing','path':'/home_assignments/data/rows'},'aggregates':{'n':{'op':'count'}}}
            result=await call('select_game_state',{'spec':{'queries':[query],'expected_snapshot_id':snapshot.snapshot_id,'include_ui_context':True}})
            assert result['state']['snapshot_id']==snapshot.snapshot_id and result['state']['session_id']==snapshot.session_id and result['ui_context']==snapshot.ui_context
            assert result['results'][0]['rows']==[{'n':len(expected[i])}]
        publish(0)
        restored=await call('query_game_state',{'domain':'housing','pointer':'/home_assignments/data','expected_snapshot_id':snapshots[0].snapshot_id})
        assert restored['data']['rows']==expected[0]
        refusal=await call('select_game_state',{'spec':{'queries':[query],'expected_snapshot_id':snapshots[-1].snapshot_id}},error=True);assert 'Snapshot changed' in refusal
    return {'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),
      'scope':'Six unchanged production home/roster/cohort observations during finite speed-one copied-city progression; public direct-getter parity, retained-original MCP relationships and cache/pin transitions.',
      'samples':6,'simulation_ticks_advanced':ticks[-1]-ticks[0],'simulation_seconds_advanced':seconds[-1]-seconds[0],
      'home_row_counts':[e['home_rows'] for e in samples],'relationship_row_counts':[len(e) for e in expected],
      'observed_roster_sequence_transitions':sum(a!=b for a,b in zip(expected,expected[1:])),
      'observed_recorded_pair_multiset_transitions':sum(a!=b for a,b in zip(pair_multisets,pair_multisets[1:])),
      'same_callback_direct_getter_parity':True,'retained_original_relationship_parity':True,'snapshot_cache_replacement_and_old_pin_refusal':True,'revisited_original_not_recomputed_from_latest_game':True,
      'actual_mcp_calls':calls,'provider_calls':0,'explicit_fixture_save_requests':0,'production_payload_unchanged':True,
      'mod_jar_sha256':manifest['mod_jar_sha256'],'production_source_sha256':manifest['validation']['production_source_sha256'],'python_source_sha256':manifest['validation']['python_source_sha256'],
      'source_sha256':{n:sha(ROOT/n) for n in SOURCES},'selected_game_source_sha256':GAME_SOURCE_HASHES,
      'private_observation_sha256':[sha(state/e['file']) for e in samples],
      'manual_source_review':['GAME.updateI also advances when the simulation speed is zero, so tick changes alone cannot establish unpaused simulation. TIME.currentSecond returns the stored simulation clock; six strictly increasing values are required separately.',
        'GameSpeed.speedSet changes requested/actual speed. These controls and view activation are test-only in the isolated profile, not production commands.',
        'GAME update invokes automatic saving as normal simulation progresses. The fixture makes no explicit save request; any engine autosave belongs only to the isolated copied profile, and no zero-engine-save assertion is made.'],
      'public_test_only_actions':['VIEW.s.activate','GAME.SPEED.speedSet(1), speedSet(0) after six samples','GAME.addAfterUpdate, CORE.annihilate for isolated fixture'],
      'limits':['Finite naturally progressing copied city. Roster-sequence changes can reflect index/order changes; pair-multiset transitions are reported separately. No forced reassignment or permanent identity claim; unchanged samples establish no reassignment case. Direct getter agreement does not independently audit private storage.',
        'Each observation is copied on one callback. MCP checks use original retained snapshots after the six samples, not concurrent live query servicing or one transaction across different ticks.',
        'Private mailbox replacement exercises real production cache invalidation and wrong-pin refusal. Original timestamps are preserved; no substitution into the live game mailbox.',
        'No housing assignment, furnishing, policy or resource-use mutation is performed by this fixture. Normal simulation can change disposable in-memory state; no all-engine rollback claim. The supplied copied save stays unchanged. Normal simulation may write its own disposable automatic saves; no zero-engine-save claim.',
        'Not maximum scan/row/roster/relation/byte, native roster errors, invalid isolation, large-city/FPS, all menus or immediate unload acceptance. No new production capability or player release is implied.']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['game-dir','jdk-home','java','save']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--candidate-dir',type=Path);p.add_argument('--validation',type=Path)
    a=p.parse_args();review=json.loads((ROOT/'HOUSING_CONTRACT_REVIEW.json').read_text());assert review['passed']
    for n,h in review['source_sha256'].items():assert sha(ROOT/n)==h,n
    assert sha(a.game_dir/'SongsOfSyx.jar')==review['game_jar_sha256'] and sha(a.game_dir/'info/SongsOfSyx-sources.jar')==review['source_archive_sha256']
    with zipfile.ZipFile(a.game_dir/'info/SongsOfSyx-sources.jar') as z:GAME_SOURCE_HASHES={n:hashlib.sha256(z.read(n)).hexdigest() for n in GAME_SOURCES}
    with exclusive_fixture():
        run(a,scenario_override=ROOT/'dev/candidates/housing/running/StockpileScenario.java',extra_sources=[],verifier=verify,
          report_name='housing-running-validation.json',boundary_review_path=ROOT/'HOUSING_CONTRACT_REVIEW.json',
          completion_marker=('housing-running-clean-exit.json',{'passed':True,'samples':6}))
