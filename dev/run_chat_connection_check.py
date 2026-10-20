"""Build preflight or validate an exact paid candidate's automatic connection, without inference.

Never promotes a release. Uses only copied save/profile and the shared fixture lock.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from game_fixture_lock import exclusive_fixture
from native_game_completion import require_clean_game_log
from run_player_chat_check import native_environment
from make_user_test import MODULES


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(args):
    runtime=(ROOT/'runtime').resolve();home=runtime/'smoke-home';save=args.save.resolve()
    if home.is_symlink() or not home.is_dir() or not save.is_file() or not save.is_relative_to(runtime):
        raise ValueError('Use isolated smoke-home and a copied save under runtime/')
    target=home/'.local/share/songsofsyx/mods/syx-ai-assistant/V71/script/syx-ai-assistant.jar'
    if target.is_symlink() or not target.is_file() or not target.resolve().is_relative_to(home):
        raise ValueError('Copied mod must remain in smoke-home')
    state=Path(tempfile.mkdtemp(prefix='chat-auto-',dir=runtime));os.chmod(state,0o700)
    game=args.game_dir.resolve();jdk=args.jdk_home.resolve();java=args.java.resolve()
    env=native_environment(os.environ);env['PYTHONPATH']=str(ROOT);env['SYX_JAVA_HOME']=str(jdk)
    sources={str(p.relative_to(ROOT/'mod/src/main/java')):sha(p) for p in (ROOT/'mod/src/main/java').rglob('*.java')}
    python={n+'.py':sha(ROOT/(n+'.py')) for n in MODULES}
    if args.mod_jar:
        if not args.validation:raise ValueError('A fixed JAR requires its matching paid candidate report')
        report=json.loads(args.validation.read_text());jar=args.mod_jar.resolve()
        if not report.get('passed') or not report.get('real_provider_round_trip') or report.get('requested_model')!='deepseek-v4-pro' or report.get('mod_jar_sha256')!=sha(jar) or report.get('production_source_sha256')!=sources or report.get('python_source_sha256')!=python:
            raise ValueError('Supplied paid candidate is not current source/JAR')
    else:
        for script,extra in [('audit_api.py',[]),('build_mod.py',['--output',str(state/'candidate')])]:
            with (state/(script+'.log')).open('w') as log:
                subprocess.run([sys.executable,str(ROOT/script),'--game-dir',str(game),*extra],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        jar=state/'candidate/syx-ai-assistant/V71/script/syx-ai-assistant.jar'
    audit=json.loads((ROOT/'api-audit.json').read_text())
    if audit['mod_source_sha256']!=sources or sha(game/'SongsOfSyx.jar')!=audit['game_jar_sha256'] or sha(game/'info/SongsOfSyx-sources.jar')!=audit['source_archive_sha256']:
        raise ValueError('Current game/source/audit pairing differs')
    classes=state/'classes';classes.mkdir()
    subprocess.run(['java','-Djava.home='+str(jdk),'-m','jdk.compiler/com.sun.tools.javac.Main','--release','16','-encoding','UTF-8',
        '-cp',str(game/'SongsOfSyx.jar')+os.pathsep+str(jar),'-d',str(classes),*map(str,(ROOT/'mod/tests').glob('*.java'))],env=env,check=True)
    backup=state/'prior-mod.jar';shutil.copy2(target,backup);save_before=sha(save)
    cp=os.pathsep.join(map(str,[game/'SongsOfSyx.jar',game/'base/script/000_Tutorial.jar',game/'base/script/001_Tutorial.jar',jar,classes]))
    flag='chat' if args.case=='focus' else 'chatAuto'
    command=[str(java),'-Xmx4g','-Duser.home='+str(home),'-Dsyx.assistant.stateDir='+str(state),'-Dsyx.smoke.'+flag+'=true','-cp',cp,'LiveSmoke',str(save)]
    native=verifier=None
    try:
        shutil.copy2(jar,target)
        subprocess.run([*command[:-2],'-Dsyx.smoke.validateOnly=true',*command[-2:]],cwd=game,env=env,check=True)
        with (state/'game.log').open('w') as glog,(state/'verifier.log').open('w') as vlog:
            verifier=subprocess.Popen([sys.executable,str(ROOT/'dev/verify_auto_connection.py'),'--state-dir',str(state),'--case',args.case],cwd=ROOT,env=env,stdout=vlog,stderr=subprocess.STDOUT)
            native=subprocess.Popen(command,cwd=game,env=env,stdout=glog,stderr=subprocess.STDOUT)
            verifier.wait(timeout=235)
            if verifier.returncode:raise RuntimeError('Automatic connection verifier failed; inspect private logs: '+str(state))
            native.wait(timeout=30)
            if native.returncode:raise RuntimeError('Native automatic connection fixture failed: '+str(state))
        require_clean_game_log(state/'game.log')
        completion=json.loads((state/('chat-focus-clean-exit.json' if args.case=='focus' else 'auto-clean-exit.json')).read_text())
        expected={'passed':True,'provider_turns':0} if args.case=='focus' else {'passed':True,'turns':2,'reloads':1}
        if completion!=expected or (state/'auto-fixture-failure.json').exists():raise RuntimeError('Missing explicit clean completion')
        report=json.loads((state/'auto-connection-validation.json').read_text());assert report['passed']
    finally:
        for process in [verifier,native]:
            if process is not None and process.poll() is None:
                process.terminate()
                try:process.wait(timeout=15)
                except subprocess.TimeoutExpired:process.kill();process.wait()
        shutil.copy2(backup,target)
        if sha(target)!=sha(backup) or sha(save)!=save_before:raise RuntimeError('Copied mod/save restoration failed; no passing report')
    report.update(validated_at=datetime.now(timezone.utc).isoformat(),case=args.case,stage='Exact paid candidate feature check' if args.mod_jar else 'Built-source native preflight; not paid release acceptance',
        mod_jar_sha256=sha(jar),production_source_sha256=sources,python_source_sha256=python,
        game_jar_sha256=audit['game_jar_sha256'],source_archive_sha256=audit['source_archive_sha256'],
        known_engine_crash_markers_absent=True,explicit_fixture_clean_completion=True,game_exit_code=0,
        copied_profile_mod_restored=True,copied_save_unchanged=True,
        fixture_source_sha256={n:sha(ROOT/n) for n in ['dev/run_chat_connection_check.py','dev/verify_auto_connection.py','mod/tests/ChatAutoConnectScenario.java','mod/tests/ChatUiScenario.java','mod/tests/LiveSmoke.java','dev/native_game_completion.py']})
    output=state/'connection-validation.json';output.write_text(json.dumps(report,indent=2)+'\n')
    print('Automatic connection evidence:',output,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('game-dir','save','java','jdk-home'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--mod-jar',type=Path);p.add_argument('--validation',type=Path)
    p.add_argument('--case',choices=['connection','focus'],default='connection')
    args=p.parse_args()
    with exclusive_fixture():run(args)
