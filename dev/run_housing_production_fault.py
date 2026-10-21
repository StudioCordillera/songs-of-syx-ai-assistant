"""One controlled missing-furnishing capacity getter failure; public copied-city fixture only."""
import argparse,json,sys,hashlib,zipfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from game_fixture_lock import exclusive_fixture
from run_stockpile_probe import run,sha
from housing_mcp_checks import check as check_mcp

SOURCES=['dev/candidates/housing/production-fault/StockpileScenario.java','mod/src/main/java/syx/assistant/HousingObservation.java',
 'dev/run_housing_production_fault.py','dev/run_stockpile_probe.py','mod/tests/LiveSmoke.java','dev/native_game_completion.py']
GAME_SOURCES=['settlement/room/main/MapDataF.java','settlement/room/home/house/HomeInstance.java',
 'settlement/room/home/house/HomeContructor.java','settlement/room/home/house/Sprites.java','settlement/room/sprite/RoomSprite.java']

async def verify(state,manifest):
    fixture=state/'stockpile-fixture.json';r=json.loads(fixture.read_text());assert r['passed'] and r['fault_cases']==1
    assert r['direct_getter_failure']=='NullPointerException' and r['failed_room_reads']==1
    assert r['baseline_home_rows']==r['fault_home_rows']+1 and r['fault_home_rows']>0
    for k in ['unrelated_rows_ledger_unchanged','housing_output_restored','same_callback']:assert r[k] is True
    mcp_checks=[await check_mcp(state,'housing-fault-observation.json',failed_rooms=1),await check_mcp(state,'housing-restored-observation.json')]
    return {'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),
      'scope':'Production housing capacity-getter failure after public furnishing clear, actual MCP failure diagnostics/relationships, and same-callback DTO restoration.',
      'native_checks':r,'production_mcp_checks':mcp_checks,'mod_jar_sha256':manifest['mod_jar_sha256'],'production_source_sha256':manifest['validation']['production_source_sha256'],'python_source_sha256':manifest['validation']['python_source_sha256'],
      'actual_housing_mcp_calls':sum(c['actual_mcp_calls'] for c in mcp_checks),'provider_calls':0,'save_writes':0,'production_housing_mapping':True,
      'housing_static_review_sha256':sha(ROOT/'HOUSING_BOUNDARY_REVIEW.json'),'source_sha256':{n:sha(ROOT/n) for n in [*SOURCES,'dev/housing_mcp_checks.py','syx_housing.py','syx_mcp.py']},
      'selected_game_source_sha256':GAME_SOURCE_HASHES,'private_fixture_sha256':sha(fixture),
      'public_test_only_actions':['MapDataF.itemClear','MapDataF.itemSet in finally','GAME.SPEED.speedSet/VIEW.s.activate'],
      'manual_source_review':['HomeInstance.it reads furnishing at the service tile; occupantsMax dereferences its group. Clearing the furnishing through public itemClear therefore induces a real missing-item capacity getter exception without private state access.',
        'MapDataF.itemClear changes furnishing/sprite/light data and checks room ownership; itemSet repopulates the full footprint. The test selects a complete same-room footprint and restores inside finally before yielding. Housing construction uses the reviewed Dummy sprite on these furnishing tiles.',
        'Only candidate DTO equality, original item identity and unrelated row/ledger equality are restored/checked. Sprite randomness, light/cache/path or all engine-state rollback is not claimed. No public mutation becomes part of the observer.'],
      'limits':['One deliberately induced missing furnishing, not a naturally corrupt save, null room registry, invalid isolation, stale resident ID, roster error or every exception type.',
        'The failed room is omitted with failed_room_reads=1; all other rows/cohort ledger stay equal. Complete slot scanning does not mean complete successful housing observation.',
        'Same-original-snapshot production MCP count/relationship and failure-diagnostic checks are included; battle/setup/reload remain separate scene tests. No source-private/reflection/process-memory/invocation workaround, save or normal-profile mutation.']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['game-dir','jdk-home','java','save']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--candidate-dir',type=Path);p.add_argument('--validation',type=Path)
    a=p.parse_args();review=json.loads((ROOT/'HOUSING_BOUNDARY_REVIEW.json').read_text());assert review['passed']
    for n,h in review['source_sha256'].items():assert sha(ROOT/n)==h
    assert sha(a.game_dir/'SongsOfSyx.jar')==review['game_jar_sha256'] and sha(a.game_dir/'info/SongsOfSyx-sources.jar')==review['source_archive_sha256']
    with zipfile.ZipFile(a.game_dir/'info/SongsOfSyx-sources.jar') as z:GAME_SOURCE_HASHES={n:hashlib.sha256(z.read(n)).hexdigest() for n in GAME_SOURCES}
    with exclusive_fixture():
        run(a,scenario_override=ROOT/'dev/candidates/housing/production-fault/StockpileScenario.java',
          extra_sources=[],verifier=verify,
          report_name='housing-production-fault-validation.json',boundary_review_path=ROOT/'HOUSING_BOUNDARY_REVIEW.json',
          completion_marker=('housing-fault-clean-exit.json',{'passed':True,'fault_cases':1,'housing_output_restored':True}))
