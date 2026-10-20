"""Public construction/removal of an empty chamber and real candidate scan/row limits. Copied fixture only."""
import argparse,json,sys,hashlib,zipfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from game_fixture_lock import exclusive_fixture
from run_stockpile_probe import run,sha

SOURCE_PATHS=['settlement/room/home/chamber/Constructor.java','settlement/room/home/chamber/ChamberInstance.java',
 'settlement/room/home/chamber/ROOM_CHAMBER.java','settlement/room/main/TmpArea.java','settlement/room/main/MapDataF.java',
 'settlement/room/main/RoomInstance.java','settlement/room/main/furnisher/Furnisher.java',
 'settlement/room/main/furnisher/FurnisherItem.java','settlement/room/main/ROOMS.java','settlement/room/main/Room.java','settlement/stats/colls/StatsHome.java','game/nobility/NOBLES.java','game/nobility/Noble.java','settlement/entity/humanoid/Humanoid.java','settlement/entity/humanoid/ai/main/AIManager.java','init/type/HTYPES.java','init/type/CAUSE_ARRIVES.java']

async def verify(state,manifest):
    fixture=state/'stockpile-fixture.json';r=json.loads(fixture.read_text())
    assert r['passed'] and r['created_empty_chambers']==r['removed_chambers']==1
    assert r['occupied_chamber_cases']==1 and r['prior_noble_assignment_restored'] is True and r['test_subjects_created_promoted']==1 and r['row_budget_cases']==1 and r['scan_prefix_cases']==3
    for k in ['empty_chamber_scalar_roster_parity','ordinary_ledger_unchanged','baseline_rows_restored']:assert r[k] is True
    assert r['ordinary_baseline_rows']>0 and 0<r['placement_candidates_checked']<=10000
    names=['dev/candidates/housing-chamber/StockpileScenario.java','dev/candidates/housing/syx/assistant/candidate/HousingObservation.java',
      'dev/run_housing_chamber.py','dev/run_stockpile_probe.py','mod/tests/LiveSmoke.java','dev/native_game_completion.py']
    with zipfile.ZipFile(GAME_DIR/'info/SongsOfSyx-sources.jar') as z:
        sources={n:hashlib.sha256(z.read(n)).hexdigest() for n in SOURCE_PATHS}
    return {'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),
      'scope':'Developer-only real empty/occupied chamber assignment/restoration and removal and bounded home candidate reads in one paused copied city.',
      'native_checks':r,'mod_jar_sha256':manifest['mod_jar_sha256'],'production_source_sha256':manifest['validation']['production_source_sha256'],
      'candidate_packaged_in_player':False,'candidate_housing_mcp_calls':0,'provider_calls':0,'save_writes':0,
      'housing_static_review_sha256':sha(ROOT/'HOUSING_BOUNDARY_REVIEW.json'),
      'source_sha256':{n:sha(ROOT/n) for n in names},'selected_game_source_sha256':sources,'private_fixture_sha256':sha(fixture),
      'public_test_only_actions':['ROOMS.tmpArea/set','MapDataF.itemSet','Furnisher.create with RoomInit','ROOMS.stats.finished.add','Room.remove/TmpArea.clearAndUpdate','GAME.SPEED.speedSet/VIEW.s.activate','Humanoid constructor/nobleSet for one fresh fixture subject','STATS.HOME.GETTER.set for that fixture noble; prior null home restored in finally'],
      'manual_source_review':['The fixed paired chamber furnishing item is index one, six by seven. The test requires free accessible room/furnishing slots before creating a temporary area; public furnishing placement supplies the bed tile required by the real chamber constructor.',
        'RoomInstance consumes/replaces the temporary area, registers the instance and computes isolation. Chamber creation initializes service coordinate, jobs and staffing and activates the room. These are deliberate disposable-fixture mutations, never observer operations.',
        'Removal disposes the empty chamber and clears its area through the public route. A fresh subject is constructed from an existing race example and promoted through Humanoid.nobleSet; entity registration/type/noble/canOccupy checks must pass. The StatsHome setter assigns it, then restores the prior null assignment in finally. No existing person is promoted or reassigned; no direct HOME occupancy/policy/resource-use action is invoked. Candidate reads run synchronously in the same after-update callback, before simulation resumes.',
        'Noble.subject can clear a stale subjectID on lookup; it is excluded from the candidate reader. The initial native attempt requiring an existing noble failed and is excluded from acceptance.',
        'The source/bytecode review of the unchanged reader remains separate. This report adds actual empty-chamber, prefix/row-bound and removal evidence; it checks one occupied roster/recorded-coordinate linkage, not natural noble behavior, and does not turn construction/assignment into production commands.'],
      'limits':['One deliberately constructed empty chamber in a paused copied city, one new test-only subject promoted to noble, temporarily assigned and returned to its prior null home; not natural noble housing behavior or stale chamber IDs.',
        'One actual row-cap case and three exact scan-prefix cases; no 10000-slot/1000-row maximum population, byte overflow, invalid isolation, missing resident or exception injection acceptance.',
        'No battle/setup/reload, live simulation, effective eligibility, physical bed quality, UI selection, permanent room identity or native MCP integration acceptance.',
        'The fresh test noble remains in memory until process exit. Construction/promotion/assignment/removal can change population, AI, nobility, caches, statistics, tile decoration/path/maintenance counters; no universal in-memory rollback claim. Normal saves stay untouched and the supplied copied save remains unchanged.']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['game-dir','jdk-home','java','save']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--candidate-dir',type=Path);p.add_argument('--validation',type=Path)
    a=p.parse_args();GAME_DIR=a.game_dir;review=json.loads((ROOT/'HOUSING_BOUNDARY_REVIEW.json').read_text());assert review['passed']
    for n,h in review['source_sha256'].items():assert sha(ROOT/n)==h,'Housing candidate/reviewer changed'
    assert sha(a.game_dir/'SongsOfSyx.jar')==review['game_jar_sha256'] and sha(a.game_dir/'info/SongsOfSyx-sources.jar')==review['source_archive_sha256']
    with zipfile.ZipFile(a.game_dir/'info/SongsOfSyx-sources.jar') as z:
        for n in SOURCE_PATHS:z.getinfo(n)
    with exclusive_fixture():
        run(a,scenario_override=ROOT/'dev/candidates/housing-chamber/StockpileScenario.java',
          extra_sources=[ROOT/'dev/candidates/housing/syx/assistant/candidate/HousingObservation.java'],verifier=verify,
          report_name='housing-chamber-validation.json',boundary_review_path=ROOT/'HOUSING_BOUNDARY_REVIEW.json',
          completion_marker=('housing-chamber-clean-exit.json',{'passed':True,'created_empty_chambers':1,'removed_chambers':1}))
