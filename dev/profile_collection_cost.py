"""Profile the shipped collector in an isolated copied city, then parse/select offline.

Requires the licensed installation, Java/JDK and copied runtime/smoke.save/profile.
No inference, screenshots, native input or normal saves. Does not change production.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time
import zipfile

ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from check_user_test_release import check
from benchmark_selective_queries import benchmark
from syx_mcp import Snapshot
from syx_query import QueryEngine


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def distribution(values):
    ordered=sorted(values)
    return {'min':round(min(values),3),'median':round(statistics.median(values),3),
        'p95':round(ordered[int(.95*(len(ordered)-1))],3),'max':round(max(values),3)}


def analyze(directory,manifest):
    fixture=json.loads((directory/'collection-cost-fixture.json').read_text())
    samples=fixture['samples'];assert fixture['passed'] and len(samples)==32
    assert samples[0]['cache']=='cold_mod_help_cache' and all(s['cache']=='warm_mod_help_cache' for s in samples[1:])
    raw=(directory/'collection-observation.json').read_bytes();snapshot=Snapshot.model_validate_json(raw)
    assert not snapshot.demo and snapshot.game_loaded and snapshot.scene['settlement_scene_kind']=='city'
    assert fixture['domain_count']==len(snapshot.domains)==18
    assert fixture['reference_count']==len(snapshot.references)
    # This fixed record is deliberately not refreshed or served as a current observation.
    five_queries=benchmark(directory/'collection-observation.json',31)
    counter=json.loads((ROOT/'service-query-example.json').read_text())
    policy=json.loads((ROOT/'service-policy-query-example.json').read_text())
    spec={'queries':counter['queries']+policy['queries']}
    workforce={r['room_id']:r for r in snapshot.domains['employment'].data['rooms']}
    services=snapshot.domains['services'].data
    positive=[r for r in services['room_data']['rooms'] if r['total_slots_raw']>0]
    expected_counter=[{'room':r['room_id'],'blueprint':r['blueprint_id'],'active':r['active'],
        'total_slots':r['total_slots_raw'],'available_slots':r['available_slots_raw'],'reserved_slots':r['reserved_slots_raw'],
        'staffing':workforce.get(r['room_id'])} for r in positive[:5]]
    cohorts={(r['race_id'],r['class_id']):r['count'] for r in snapshot.domains['population'].data['by_race_class']}
    denied=[r for r in services['access_policy']['cohort_rules'] if not r['allowed_by_configured_rule'] and (r['race_id'],r['class_id']) in cohorts]
    expected_policy=[{'service':r['service_id'],'blueprint':r['blueprint_id'],'race':r['race_id'],'class':r['class_id'],
        'configured_allow':False,'scene_population':cohorts[r['race_id'],r['class_id']]} for r in denied[:5]]
    result=QueryEngine(snapshot).execute(spec)
    assert [r['rows'] for r in result]==[expected_counter,expected_policy]
    assert [r['matched_total'] for r in result]==[len(positive),len(denied)]
    parsing=[];query=[]
    for _ in range(31):
        start=time.perf_counter_ns();parsed=Snapshot.model_validate_json(raw);end=time.perf_counter_ns()
        parsing.append((end-start)/1e6)
        start=time.perf_counter_ns();observed=QueryEngine(parsed).execute(spec);end=time.perf_counter_ns()
        assert observed==result;query.append((end-start)/1e6)
    return {'passed':True,'measured_at':datetime.now(timezone.utc).isoformat(),
        'game_version':snapshot.game_version,'mod_jar_sha256':manifest['mod_jar_sha256'],
        'production_source_sha256':manifest['validation']['production_source_sha256'],
        'python_source_sha256':manifest['validation']['python_source_sha256'],
        'private_observation_sha256':hashlib.sha256(raw).hexdigest(),'observed_at':str(snapshot.captured_at),
        'native_fixture':fixture,'sample_counts':{'cold_reference_cache':1,'warm_reference_cache':31,'offline_parse_and_service_queries':31},
        'timing_unit':'milliseconds of monotonic elapsed time',
        'quantile_method':'Sorted samples, zero-based index floor(0.95*(n-1)); descriptive sample percentile, not a statistical bound.',
        'warm_native_ms':{label:distribution([s[key]/1e6 for s in samples[1:]]) for key,label in
            [('collection_ns','collection'),('encoding_utf8_ns','json_and_utf8_encoding'),('combined_ns','combined_fixture_work')]},
        'cold_native_ms':{label:round(samples[0][key]/1e6,3) for key,label in
            [('collection_ns','collection'),('encoding_utf8_ns','json_and_utf8_encoding'),('combined_ns','combined_fixture_work')]},
        'snapshot_bytes':len(raw),'offline_parse_ms':distribution(parsing),'offline_two_service_queries_ms':distribution(query),
        'two_service_queries_independent_parity':True,'five_existing_query_examples':five_queries,
        'selected_two_service_results_bytes':len(json.dumps(result).encode()),
        'source_sha256':{n:sha(ROOT/n) for n in ['mod/tests/LiveSmoke.java','mod/tests/CollectionCostScenario.java',
            'dev/profile_collection_cost.py','dev/benchmark_selective_queries.py','selective-query-examples.json',
            'service-query-example.json','service-policy-query-example.json']},
        'inference_calls':0,
        'limits':fixture['limits']+['The fixture encodes on its callback thread to isolate elapsed cost. Production encoding runs in the export worker; combined_fixture_work is not a measured production game-thread stall.',
            'Local descriptive timings include scheduling/GC/host noise; not an FPS/SLA/worst-case guarantee.',
            'Offline parsing excludes disk read. Offline query timings exclude parsing, MCP transport, freshness validation, UI envelopes and model latency.',
            'One cold sample is not a statistical cold-start bound. No load/save/paused-menu/all-scene or larger-city latency acceptance.',
            'Selected result size excludes outer MCP/status/UI envelopes. Configured false flags do not count actually barred people.']}


def profile(args):
    manifest=check();runtime=ROOT/'runtime';save=args.save.resolve();home=runtime/'smoke-home'
    if home.is_symlink() or not home.is_dir() or not save.is_relative_to(runtime.resolve()):
        raise ValueError('Use the existing isolated smoke-home and a copied save under runtime/')
    directory=runtime/('collection-cost-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'));directory.mkdir()
    jar=directory/'syx-ai-assistant.jar'
    with zipfile.ZipFile(ROOT/'releases/latest-user-test.zip') as archive:jar.write_bytes(archive.read('mod/syx-ai-assistant/V71/script/syx-ai-assistant.jar'))
    assert sha(jar)==manifest['mod_jar_sha256']
    env={k:v for k,v in os.environ.items() if not any(s in k for s in ['API_KEY','ACCESS_TOKEN','REFRESH_TOKEN'])};env['PYTHONPATH']=str(ROOT)
    game=args.game_dir.resolve();classes=directory/'classes';classes.mkdir()
    subprocess.run(['java','-Djava.home='+str(args.jdk_home.resolve()),'-m','jdk.compiler/com.sun.tools.javac.Main',
        '--release','16','-encoding','UTF-8','-cp',str(game/'SongsOfSyx.jar')+':'+str(jar),'-d',str(classes),
        *[str(p) for p in (ROOT/'mod/tests').glob('*.java')]],env=env,check=True)
    target=home/'.local/share/songsofsyx/mods/syx-ai-assistant/V71/script/syx-ai-assistant.jar'
    assert target.parent.is_dir() and not target.is_symlink();shutil.copy2(jar,target)
    cp=':'.join(map(str,[game/'SongsOfSyx.jar',game/'base/script/000_Tutorial.jar',game/'base/script/001_Tutorial.jar',jar,classes]))
    command=[str(args.java.resolve()),'-Xmx4g','-Duser.home='+str(home),'-Dsyx.assistant.stateDir='+str(directory),
        '-Dsyx.smoke.collectionCost=true','-cp',cp,'LiveSmoke',str(save)]
    subprocess.run([*command[:-2],'-Dsyx.smoke.validateOnly=true',*command[-2:]],cwd=game,env=env,check=True)
    with (directory/'game.log').open('w') as log:
        process=subprocess.Popen(command,cwd=game,env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+100
            while time.monotonic()<deadline:
                if (directory/'collection-cost-fixture.json').exists():break
                if process.poll() is not None:raise AssertionError('Game exited before profile')
                time.sleep(.2)
            else:raise AssertionError('Collection profile timed out')
            report=analyze(directory,manifest)
            (directory/'verifier.done').write_text('profile complete\n')
            process.wait(timeout=30);assert process.returncode==0
        finally:
            (directory/'verifier.done').write_text('verifier finished\n')
            if process.poll() is None:
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=15)
    report['game_exit_code']=process.returncode
    (directory/'collection-cost-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Collection cost evidence:',directory/'collection-cost-validation.json',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['game-dir','save','java','jdk-home']:p.add_argument('--'+name,type=Path,required=True)
    from game_fixture_lock import exclusive_fixture
    args=p.parse_args()
    with exclusive_fixture():profile(args)
