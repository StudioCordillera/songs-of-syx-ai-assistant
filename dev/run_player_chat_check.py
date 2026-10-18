"""Build/audit and run two real DeepSeek Pro fixture turns using a manually supplied key.

Paid integration test, never part of pytest/CI. Uses only the isolated runtime/smoke-home
and a copied save under runtime/. No credential is written or passed to the game/MCP.
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
import time

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'dev'))
from syx_chat_service import read_key_file
from verify_user_test_chat import verify
from game_fixture_lock import exclusive_fixture


def native_environment(env):
    return {k:v for k,v in env.items() if not any(marker in k.upper() for marker in
        ('API_KEY','ACCESS_TOKEN','REFRESH_TOKEN','OAUTH_TOKEN','AUTH_TOKEN'))}


def run(args):
    key=read_key_file(args.env_file) if args.env_file else os.environ.get('DEEPSEEK_API_KEY','')
    if not key.strip():raise ValueError('Supply DEEPSEEK_API_KEY in the environment or an explicit --env-file. This test makes real paid requests.')
    runtime=(ROOT/'runtime').resolve();home=runtime/'smoke-home';save=args.save.resolve()
    if home.is_symlink() or not home.is_dir() or not save.is_relative_to(runtime) or not save.is_file():
        raise ValueError('Create runtime/smoke-home and a copied save under runtime/; never use the normal profile/save')
    game=args.game_dir.resolve();jdk=args.jdk_home.resolve();java=args.java.resolve()
    for p in [game/'SongsOfSyx.jar',game/'info/SongsOfSyx-sources.jar',java]:
        if not p.is_file():raise ValueError('Required licensed game/source or Java executable is missing')
    target=home/'.local/share/songsofsyx/mods/syx-ai-assistant'
    if target.is_symlink() or not target.resolve().is_relative_to(home.resolve()):
        raise ValueError('Isolated mod folder must stay inside the fixture home without symlink escape')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f');state=runtime/('player-chat-'+stamp)
    state.mkdir(mode=0o700);history=state/'history';history.mkdir(mode=0o700)
    env=native_environment(os.environ);env['PYTHONPATH']=str(ROOT);env['SYX_JAVA_HOME']=str(jdk)
    # Build and audit this checkout, rather than labeling an arbitrary old JAR as current source.
    for script,extra in [('audit_api.py',[]),('build_mod.py',['--output',str(state/'candidate')])]:
        with (state/(script+'.log')).open('w') as log:
            subprocess.run([sys.executable,str(ROOT/script),'--game-dir',str(game),*extra],cwd=ROOT,env=env,
                           stdout=log,stderr=subprocess.STDOUT,check=True)
    jar=state/'candidate/syx-ai-assistant/V71/script/syx-ai-assistant.jar'
    classes=state/'classes';classes.mkdir()
    subprocess.run(['java','-Djava.home='+str(jdk),'-m','jdk.compiler/com.sun.tools.javac.Main','--release','16',
        '-encoding','UTF-8','-cp',str(game/'SongsOfSyx.jar')+os.pathsep+str(jar),'-d',str(classes),
        *map(str,(ROOT/'mod/tests').glob('*.java'))],cwd=ROOT,env=env,check=True)
    backup=state/'prior-isolated-mod'
    if target.exists():shutil.copytree(target,backup)
    target.parent.mkdir(parents=True,exist_ok=True)
    try:
        if target.exists():shutil.rmtree(target)
        shutil.copytree(jar.parents[2],target)
        cp=os.pathsep.join(map(str,[game/'SongsOfSyx.jar',game/'base/script/000_Tutorial.jar',game/'base/script/001_Tutorial.jar',jar,classes]))
        command=[str(java),'-Xmx4g','-Duser.home='+str(home),'-Dsyx.assistant.stateDir='+str(state),
            '-Dsyx.smoke.chatLive=true','-Dsyx.smoke.chatSelect=true','-cp',cp,'LiveSmoke',str(save)]
        subprocess.run([*command[:-2],'-Dsyx.smoke.validateOnly=true',*command[-2:]],cwd=game,env=env,check=True)
        coordinator_env={**env,'DEEPSEEK_API_KEY':key}
        with (state/'coordinator.log').open('w') as clog,(state/'game.log').open('w') as glog:
            coordinator=subprocess.Popen([sys.executable,'-m','syx_chat_service','--state-dir',str(state),
                '--history-dir',str(history)],cwd=ROOT,env=coordinator_env,stdout=clog,stderr=subprocess.STDOUT)
            try:
                deadline=time.monotonic()+30
                while not (state/'chat-ui.txt').is_file():
                    if coordinator.poll() is not None:raise RuntimeError('Coordinator exited; inspect its private runtime log')
                    if time.monotonic()>deadline:raise RuntimeError('Coordinator startup timed out')
                    time.sleep(.2)
                native=subprocess.Popen(command,cwd=game,env=env,stdout=glog,stderr=subprocess.STDOUT)
                try:
                    native.wait(timeout=440)
                    if native.returncode:raise RuntimeError('Native fixture failed; inspect its private runtime log')
                finally:
                    if native.poll() is None:native.terminate();native.wait(timeout=20)
                report=verify(ROOT,state,history,jar);report['game_exit_code']=native.returncode
                report['dev_runner_source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
                output=state/'provider-validation.json';output.write_text(json.dumps(report,indent=2)+'\n')
                print('Two actual DeepSeek Pro turns passed. Candidate JAR:',jar)
                print('Candidate validation:',output)
            finally:
                coordinator.terminate()
                try:coordinator.wait(timeout=20)
                except subprocess.TimeoutExpired:coordinator.kill();coordinator.wait()
    finally:
        if target.exists():shutil.rmtree(target)
        if backup.exists():shutil.copytree(backup,target)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['game-dir','save','java','jdk-home']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--env-file',type=Path,help='Optional private literal key file; normally inherit DEEPSEEK_API_KEY')
    a=p.parse_args()
    try:
        with exclusive_fixture():run(a)
    except (ValueError,RuntimeError) as error:raise SystemExit(str(error))
