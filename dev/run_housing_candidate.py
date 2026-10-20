"""Finite copied-city check of the unregistered fixed home/eligibility-ledger candidate."""
import argparse,json,statistics,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from game_fixture_lock import exclusive_fixture
from run_stockpile_probe import run,sha


async def verify(state,manifest):
    fixture=state/'stockpile-fixture.json';r=json.loads(fixture.read_text());assert r['passed'] and r['samples']==32
    assert r['ordinary_homes']+r['noble_chambers']>0 and r['resolved_roster_ids']>0
    assert 0<=r['assignment_coordinate_matches']<=r['resolved_roster_ids'] and r['cohort_rows']>0
    times=r.pop('collector_ns');assert len(times)==32 and all(type(t) is int and t>=0 for t in times)
    names=['dev/candidates/housing/StockpileScenario.java','dev/candidates/housing/syx/assistant/candidate/HousingObservation.java',
        'dev/run_housing_candidate.py','dev/review_housing_boundary.py','dev/run_stockpile_probe.py','mod/tests/LiveSmoke.java','dev/native_game_completion.py']
    return {'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),
        'scope':'Unregistered candidate: fixed known home types, assigned rosters and ordinary-home group-weighted ledgers in one unchanged paused copied city.',
        'native_checks':r,'collector_cost':{'interval':'Candidate collect including fixed room-slot scan, detached rows/rosters/cohort data and bounds, excluding independent baseline and encoding.',
            'samples_after_first':31,'median_ms':statistics.median(times[1:])/1e6,'max_ms':max(times[1:])/1e6},
        'mod_jar_sha256':manifest['mod_jar_sha256'],'production_source_sha256':manifest['validation']['production_source_sha256'],
        'candidate_packaged_in_player':False,'candidate_housing_mcp_calls':0,'provider_calls':0,'save_writes':0,
        'housing_static_review_sha256':sha(ROOT/'HOUSING_BOUNDARY_REVIEW.json'),
        'source_sha256':{n:sha(ROOT/n) for n in names},'private_fixture_sha256':sha(fixture),
        'limits':['One paused copied city; naturally present known ordinary/noble type counts are recorded. Zero examples of a type do not establish native acceptance for that type.',
            'Public stored/resolved getters share engine storage. Roster/home-coordinate agreement is observed linkage, never physical presence, current sleeping or universal bidirectional consistency.',
            'Cohort sums are eligibility-weighted ledgers, not unique physical beds or effective vacant housing; no overlapping-empty-home mutation fixture or actual person eligibility evaluation.',
            'No room removal/reuse, real budget/fault/roster-cap, live simulation, battle/setup/reload or large-city/FPS acceptance. Eight bad-budget cases run separately without initializing a game.',
            'The candidate reads no resource/use/search/eligibility action and returns no engine handle. The existing hCoo scratch coordinate is compared/copied immediately in this fixture only.',
            'The shared host uses explicit legacy scenario/ready-file hooks; no production home field, new tool, provider call or normal-profile change is implemented.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['game-dir','jdk-home','java','save']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--candidate-dir',type=Path);p.add_argument('--validation',type=Path)
    a=p.parse_args();review=json.loads((ROOT/'HOUSING_BOUNDARY_REVIEW.json').read_text());assert review['passed']
    for n,h in review['source_sha256'].items():assert sha(ROOT/n)==h,'Housing candidate/reviewer changed'
    assert sha(a.game_dir/'SongsOfSyx.jar')==review['game_jar_sha256'] and sha(a.game_dir/'info/SongsOfSyx-sources.jar')==review['source_archive_sha256']
    with exclusive_fixture():
        run(a,scenario_override=ROOT/'dev/candidates/housing/StockpileScenario.java',
            extra_sources=[ROOT/'dev/candidates/housing/syx/assistant/candidate/HousingObservation.java'],verifier=verify,
            report_name='housing-candidate-validation.json',boundary_review_path=ROOT/'HOUSING_BOUNDARY_REVIEW.json',
            completion_marker=('housing-clean-exit.json',{'passed':True,'samples':32}))
