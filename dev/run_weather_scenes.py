"""Unregistered weather candidate: actual existing scene/reload fixtures and restored public setter normalization."""
import argparse,asyncio,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from game_fixture_lock import exclusive_fixture
from run_stockpile_probe import run,sha
from verify_scenes import verify as scene_verify

SOURCES=['mod/tests/SceneScenario.java','mod/tests/LiveSmoke.java','dev/candidates/weather/scenes/StockpileScenario.java',
        'dev/candidates/weather/syx/assistant/candidate/WeatherObservation.java','dev/run_weather_scenes.py','dev/run_stockpile_probe.py','dev/verify_scenes.py','dev/native_game_completion.py']


async def verify(state,manifest):
    existing=await asyncio.to_thread(scene_verify,state,260,True,True,True,True)
    rows=[]
    for index in [0,1,2,3,4,6,8,9]:
        r=json.loads((state/f'weather-scene-{index}.json').read_text());c=r['candidate'];available=index in [0,1,2,6]
        assert r['phase']==index and c['available']==available and c['scope']=='instantiated_city_weather' and r['fault_restored']
        assert r['getter_comparisons']==(14 if available else 0)
        if available:assert c['tick']==r['observer_tick'] and len(c['data']['factors'])==10 and len(c['data']['flags'])==4
        else:assert c['data'] is None and c['reason']=='No completed instantiated campaign city'
        rows.append({'phase':index,'active_view':r['scene']['active_view'],'available':available,'direct_getter_comparisons':r['getter_comparisons']})
    return {'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),'scope':'Unregistered unchanged weather collector through eight actual existing scene phases; production MCP context/regressions are separately checked.',
        'weather_phases':rows,'direct_getter_comparisons':56,'public_wind_setter_normalization_cases':7,'normalized_zero_and_one_remain_available':True,
        'native_nonfinite_stored_factor_refusal_proven':False,
        'controlled_wind_value_restored_bit_exactly':True,'post_restoration_available':True,
        'existing_production_mcp_scene_checks':existing,'weather_mcp_calls':0,'provider_calls':0,
        'mod_jar_sha256':manifest['mod_jar_sha256'],'production_source_sha256':manifest['validation']['production_source_sha256'],
        'weather_static_review_sha256':sha(ROOT/'WEATHER_CANDIDATE_REVIEW.json'),
        'source_sha256':{n:sha(ROOT/n) for n in SOURCES},
        'limits':['Seven fixed inherited wind.setD controls normalize NaN/infinities/out-of-range/endpoint inputs to valid zero/one. These are not nonfinite stored getters. Each value is restored in a same-callback finally; no setter is part of the observer or production.',
            'This is not an invalid save, actual getter exception, null component, all-factor/climate/season or corrupted flag fixture.',
            'Actual generated battle deployment/menu, copied-city reload and initial/terrain setup are covered. Natural battle conclusion, standalone main-menu/unload and every menu remain unestablished.',
            'The existing MCP scene suite verifies current production context/session rotation and other read-only tables; it does not expose candidate weather data through MCP or join candidate rows to an older cached snapshot.',
            'Test-only speed/view/generation/reload actions use only public in-process APIs in a validated disposable profile. Battle generation can write its own disposable fixture saves; the supplied copied save is unchanged and normal saves are untouched.',
            'The unchanged weather candidate remains unregistered and absent from the latest playable bundle. Existing earlier native/static weather reports retain their own source scopes.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['game-dir','jdk-home','java','save']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--candidate-dir',type=Path);p.add_argument('--validation',type=Path)
    a=p.parse_args()
    for n in SOURCES:
        if not (ROOT/n).is_file():raise ValueError('Missing fixture source: '+n)
    review=json.loads((ROOT/'WEATHER_CANDIDATE_REVIEW.json').read_text());assert review['passed']
    for n,h in review['source_sha256'].items():assert sha(ROOT/n)==h
    assert sha(a.game_dir/'SongsOfSyx.jar')==review['game_jar_sha256'] and sha(a.game_dir/'info/SongsOfSyx-sources.jar')==review['source_archive_sha256']
    with exclusive_fixture():
        run(a,scenario_override=ROOT/'dev/candidates/weather/scenes/StockpileScenario.java',
            extra_sources=[ROOT/'dev/candidates/weather/syx/assistant/candidate/WeatherObservation.java'],verifier=verify,
            report_name='weather-scenes-validation.json',boundary_review_path=ROOT/'WEATHER_CANDIDATE_REVIEW.json',
            completion_marker=('weather-scenes-clean-exit.json',{'passed':True,'phases':8,'fault_restored':True}))
