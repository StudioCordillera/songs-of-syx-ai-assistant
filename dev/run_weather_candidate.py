"""Run an unregistered fixed weather reader through the shared locked disposable-game host."""
import argparse
from datetime import datetime,timezone
import json,statistics,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from run_stockpile_probe import run,sha
from game_fixture_lock import exclusive_fixture
CANDIDATE=ROOT/'dev/candidates/weather'


async def verify(state,manifest):
    fixture=json.loads((state/'stockpile-fixture.json').read_text());assert fixture['passed']
    samples=fixture['samples'];assert len(samples)==48 and all(s['getter_comparisons']==14 for s in samples)
    for phase in ['paused_city','running_city','paused_world']:
        subset=[s for s in samples if s['phase']==phase];assert len(subset)==16
        times=[s['game_seconds'] for s in subset]
        assert (times[-1]>times[0]) if phase=='running_city' else len(set(times))==1
        assert all(s['world_view_active']==(phase=='paused_world') for s in subset)
        for s in subset:
            c=s['candidate'];assert c['available'] is True and c['scope']=='instantiated_city_weather' and c['observer_phase']=='GAME.addAfterUpdate'
            assert len(c['data']['factors'])==10 and len(c['data']['flags'])==4
            assert all(type(d) in (int,float) and 0<=d<=1 for d in c['data']['factors'].values())
            assert all(type(d) is bool for d in c['data']['flags'].values())
    changed=sum(samples[16]['candidate']['data']['factors'][k]!=samples[31]['candidate']['data']['factors'][k] for k in samples[16]['candidate']['data']['factors'])
    times=[s['collector_ns'] for s in samples][1:]
    names=['dev/candidates/weather/StockpileScenario.java','dev/candidates/weather/syx/assistant/candidate/WeatherObservation.java',
        'dev/run_weather_candidate.py','dev/run_stockpile_probe.py','mod/tests/LiveSmoke.java','dev/native_game_completion.py']
    return {'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),'scope':'Unregistered candidate weather scalar/flag getter parity in one copied campaign; no weather MCP/player field.',
        'samples':48,'direct_getter_comparisons':48*14,'phase_samples':{'paused_city':16,'running_city':16,'paused_world':16},
        'city_time_advances_when_running':True,'paused_phase_time_unchanged':True,'naturally_changed_factors_during_running_window':changed,
        'maximum_candidate_json_bytes':max(s['json_bytes'] for s in samples),
        'collector_cost':{'interval':'Candidate collect including detached maps, finite checks, tick/time metadata, excluding JSON encoding and independent getter baseline.',
            'warm_samples':47,'median_ms':statistics.median(times)/1e6,'max_ms':max(times)/1e6},
        'mod_jar_sha256':manifest['mod_jar_sha256'],'production_source_sha256':manifest['validation']['production_source_sha256'],
        'candidate_packaged_in_player':False,'weather_mcp_calls':0,'provider_calls':0,'save_writes':0,
        'source_sha256':{n:sha(ROOT/n) for n in names},'private_fixture_sha256':sha(state/'stockpile-fixture.json'),
        'weather_static_review_sha256':sha(ROOT/'WEATHER_CANDIDATE_REVIEW.json'),
        'limits':['One copied campaign and short natural time window, not all seasons/climates, whole-year changes, battle/setup/unload, bad native getters/saves or large-city/FPS acceptance.',
            'Repeated public getters share engine storage. Pure detached rejection tests are separate from native corruption/fault injection.',
            'Underlying city weather remains available while the world view is active; no world-region weather or UI-selected weather object claim.',
            'Public speed/view fixture actions are controlled test-only. Speed is paused and city view restored before exit; in-memory simulation progress is discarded without saving.',
            'The shared host uses legacy StockpileScenario/stockpile-fixture filenames solely as explicit scenario/ready hooks; no stockpile reader is replaced, reinterpreted or shadowed.',
            'The candidate is not imported by production, advertised through MCP, or included in the tested player ZIP. No updated official stable mod contract is inferred.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['game-dir','jdk-home','java','save']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--candidate-dir',type=Path);p.add_argument('--validation',type=Path)
    a=p.parse_args();review=json.loads((ROOT/'WEATHER_CANDIDATE_REVIEW.json').read_text())
    assert review['passed']
    for n,h in review['source_sha256'].items():assert sha(ROOT/n)==h,'Weather candidate/static verifier changed'
    assert sha(a.game_dir/'SongsOfSyx.jar')==review['game_jar_sha256'] and sha(a.game_dir/'info/SongsOfSyx-sources.jar')==review['source_archive_sha256']
    with exclusive_fixture():
        run(a,scenario_override=CANDIDATE/'StockpileScenario.java',
            extra_sources=[CANDIDATE/'syx/assistant/candidate/WeatherObservation.java'],verifier=verify,
            report_name='weather-candidate-native-validation.json',boundary_review_path=ROOT/'WEATHER_CANDIDATE_REVIEW.json',
            completion_marker=('weather-clean-exit.json',{'passed':True,'samples':48}))
