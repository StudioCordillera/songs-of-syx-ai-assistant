"""Unregistered housing candidate: actual existing scene/reload fixture and same-callback direct getter parity."""
import argparse,asyncio,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from game_fixture_lock import exclusive_fixture
from run_stockpile_probe import run,sha
from verify_scenes import verify as scene_verify

SOURCES=['mod/src/main/java/syx/assistant/HousingObservation.java','syx_housing.py','syx_mcp.py','mod/tests/SceneScenario.java','mod/tests/LiveSmoke.java','dev/candidates/housing/scenes/StockpileScenario.java',
        'dev/candidates/housing/syx/assistant/candidate/HousingObservation.java','dev/run_housing_production_scenes.py','dev/run_stockpile_probe.py','dev/verify_scenes.py','dev/native_game_completion.py']


async def verify(state,manifest):
    existing=await asyncio.to_thread(scene_verify,state,260,True,True,True,True,True,True)
    rows=[]
    for index in [0,1,2,3,4,6,8,9]:
        r=json.loads((state/f'housing-scene-{index}.json').read_text());c=r['candidate'];available=index in [0,1,2,6]
        assert r['phase']==index and c['available']==available and c['scope']=='instantiated_city_home_records' and r['same_callback']
        if available:
            d=c['data'];assert r['home_rows_checked']==len(d['rooms'])>0
            assert r['resident_ids_checked']==sum(len(x['occupant_roster']['ids']) for x in d['rooms'])>0
            assert r['cohort_rows_checked']==len(d['ordinary_home_cohort_ledger'])>0
        else:
            assert c['data'] is None and c['reason']=='No completed instantiated campaign city'
            assert r['home_rows_checked']==r['resident_ids_checked']==r['cohort_rows_checked']==0
        rows.append({k:r[k] for k in ['phase','home_rows_checked','resident_ids_checked','cohort_rows_checked','same_callback']} | {'active_view':r['scene']['active_view'],'available':available})
    return {'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),
        'scope':'Eight actual public housing scene/reload transitions: independent fixed-reader checks and actual live production home/assignment MCP availability/null/count guards.',
        'housing_phases':rows,'existing_production_mcp_scene_checks':existing,'production_housing_mcp_calls':24,'provider_calls':0,
        'mod_jar_sha256':manifest['mod_jar_sha256'],'production_source_sha256':manifest['validation']['production_source_sha256'],'python_source_sha256':manifest['validation']['python_source_sha256'],
        'housing_static_review_sha256':sha(ROOT/'HOUSING_BOUNDARY_REVIEW.json'),'source_sha256':{n:sha(ROOT/n) for n in SOURCES},
        'limits':['City, tactical city, city return and real copied-city reload check direct scalar/roster/cohort getters in the same after-update callback. Generated battle deployment/menu and initial/terrain setup refuse with null data.',
            'Four city observations of the same copied settlement, not live-time, natural housing reassignment, every lifecycle/menu or standalone main-menu/unload acceptance.',
            'Existing production MCP scene checks verify current context/session rotation, other readonly tables and current production weather. Production housing records/derived relationships are queried live. Scene availability/count checks are finite held phases, not same-snapshot row identity acceptance; the production baseline verifier checks pinned retained originals separately.',
            'Test-only public view/generation/reload controls run inside the isolated profile. Battle generation can write its own disposable fixture saves. The supplied copied save is unchanged; normal saves are untouched.',
            'No housing mutation, provider request, roster truncation, invalid getter, maximum registry/row/byte or large-city/FPS acceptance. Earlier candidate/chamber reports retain their exact source scopes.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['game-dir','jdk-home','java','save']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--candidate-dir',type=Path);p.add_argument('--validation',type=Path)
    a=p.parse_args()
    for n in SOURCES:
        if not (ROOT/n).is_file():raise ValueError('Missing fixture source: '+n)
    review=json.loads((ROOT/'HOUSING_BOUNDARY_REVIEW.json').read_text());assert review['passed']
    for n,h in review['source_sha256'].items():assert sha(ROOT/n)==h
    assert sha(a.game_dir/'SongsOfSyx.jar')==review['game_jar_sha256'] and sha(a.game_dir/'info/SongsOfSyx-sources.jar')==review['source_archive_sha256']
    with exclusive_fixture():
        run(a,scenario_override=ROOT/'dev/candidates/housing/scenes/StockpileScenario.java',
            extra_sources=[ROOT/'dev/candidates/housing/syx/assistant/candidate/HousingObservation.java'],verifier=verify,
            report_name='housing-production-scenes-validation.json',boundary_review_path=ROOT/'HOUSING_BOUNDARY_REVIEW.json',
            completion_marker=('housing-scenes-clean-exit.json',{'passed':True,'phases':8}))
