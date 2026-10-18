"""Recheck the exact player JAR with public-API fixtures in an isolated copied game.

Development tool only. Requires licensed game files, a copied save already under
runtime/, runtime/smoke-home and a JDK. No provider calls, screenshots or native input.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from check_user_test_release import check


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(args):
    manifest=check(ROOT,args.candidate_dir,args.validation)
    runtime=ROOT/'runtime';save=args.save.resolve();home=runtime/'smoke-home'
    if home.is_symlink():raise ValueError('smoke-home must not be a symlink')
    home=home.resolve()
    if not save.is_relative_to(runtime.resolve()) or not home.is_dir():
        raise ValueError('Use a copied save under runtime and the existing smoke-home fixture profile')
    run=runtime/('player-core-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
    run.mkdir()
    jar=run/'syx-ai-assistant.jar'
    with zipfile.ZipFile((args.candidate_dir or ROOT/'releases')/'latest-user-test.zip') as archive:
        jar.write_bytes(archive.read('mod/syx-ai-assistant/V71/script/syx-ai-assistant.jar'))
    assert sha(jar)==manifest['mod_jar_sha256']
    game=args.game_dir.resolve();env={k:v for k,v in os.environ.items() if not any(s in k for s in ('API_KEY','ACCESS_TOKEN','REFRESH_TOKEN'))}
    env['PYTHONPATH']=str(ROOT)
    compiler=['java','-Djava.home='+str(args.jdk_home.resolve()),'-m','jdk.compiler/com.sun.tools.javac.Main']
    classes=run/'classes';classes.mkdir()
    subprocess.run([*compiler,'--release','16','-encoding','UTF-8','-cp',str(game/'SongsOfSyx.jar')+':'+str(jar),'-d',str(classes),*[str(p) for p in (ROOT/'mod/tests').glob('*.java')]],check=True,env=env)
    profile_mod=home/'.local/share/songsofsyx/mods/syx-ai-assistant/V71/script/syx-ai-assistant.jar'
    assert profile_mod.parent.is_dir() and not profile_mod.is_symlink();shutil.copy2(jar,profile_mod)
    classpath=':'.join(map(str,[game/'SongsOfSyx.jar',game/'base/script/000_Tutorial.jar',game/'base/script/001_Tutorial.jar',jar,classes]))
    used_fixtures=['LiveSmoke.java','WorldScenario.java','ProductionScenario.java','SceneScenario.java','ContextScenario.java','ExtendedContextScenario.java']
    fixture_hashes={'mod/tests/'+n:sha(ROOT/'mod/tests'/n) for n in used_fixtures}
    cases=[('world','verify_world.py',[],'world-validation.json'),
           ('production','verify_production.py',[], 'production-validation.json'),
           ('scenes','verify_scenes.py',['--on-demand','--tiles'],'scene-validation.json'),
           ('context','verify_installed_help.py',[],'installed-help-validation.json'),
           ('extended','verify_extended_context.py',[],'extended-validation.json')]
    results={}
    for name,verifier,extra,report_name in cases:
        state=runtime/(run.name+'-'+name);state.mkdir()
        command=[str(args.java.resolve()),'-Xmx4g','-Duser.home='+str(home),'-Dsyx.assistant.stateDir='+str(state),'-Dsyx.smoke.'+name+'=true','-cp',classpath,'LiveSmoke',str(save)]
        subprocess.run([*command[:-2],'-Dsyx.smoke.validateOnly=true',*command[-2:]],cwd=game,env=env,check=True,stdout=subprocess.DEVNULL)
        print('Checking player build:',name,flush=True)
        with (run/(name+'-game.log')).open('w') as log,(run/(name+'-verifier.log')).open('w') as verification_log:
            process=subprocess.Popen(command,cwd=game,env=env,stdout=log,stderr=subprocess.STDOUT)
            try:
                checked=subprocess.run([sys.executable,str(ROOT/'dev'/verifier),'--state-dir',str(state),*extra],cwd=ROOT,env=env,stdout=verification_log,stderr=subprocess.STDOUT,timeout=300)
                checked.check_returncode();process.wait(timeout=80)
                assert process.returncode==0,(name,process.returncode)
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:process.wait(timeout=10)
                    except subprocess.TimeoutExpired:process.kill();process.wait()
        result=json.loads((state/report_name).read_text());assert result['passed']
        results[name]=result
        print('Passed player build:',name,flush=True)
    report={'passed':True,'mod_jar_sha256':sha(jar),'production_source_sha256':manifest['validation']['production_source_sha256'],
        'python_source_sha256':manifest['validation']['python_source_sha256'],'checks':results,'inference_calls':0,
        'fixture_source_sha256':fixture_hashes,
        'verifier_source_sha256':{'dev/'+n:sha(ROOT/'dev'/n) for _,n,_,_ in cases},
        'limits':['Finite sampled scenarios and copied city; no exhaustive menu/keyboard/display or large-city acceptance.',
                  'Main-menu identity is unknown after expiry, not positively detected. Current simple chat stays closed during core scene checks.']}
    (run/'player-core-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Core evidence:',run/'player-core-validation.json',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('game-dir','save','java','jdk-home'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--candidate-dir',type=Path,help='Validate a candidate without replacing the published bundle')
    p.add_argument('--validation',type=Path,help='Matching candidate provider-check report')
    verify(p.parse_args())
