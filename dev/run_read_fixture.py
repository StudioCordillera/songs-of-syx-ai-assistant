"""Run fixed tile/entity/faction-context read regressions against an exact published/candidate player.

Uses copied save/profile, shared fixture lock, public in-process fixtures and private
logs. Default runs make no provider request. Explicit tiles --env-file enables two
paid Pro developer handoff turns; the key goes only to the verifier, never game/MCP.
No native input, screenshot or normal game/profile changes.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from check_user_test_release import check
from game_fixture_lock import exclusive_fixture
from native_game_completion import require_clean_game_log
from run_player_chat_check import native_environment

CASES={'weather':('weather','verify_weather.py','weather-validation.json'),
       'stockpile-matrix':('stockpileMatrix','verify_stockpile_matrix.py','stockpile-matrix-validation.json'),
       'stockpile-lifecycle':('stockpileLifecycle','verify_stockpile_lifecycle.py','stockpile-lifecycle-validation.json'),
       'stockpile-live':('stockpileLive','verify_live_stockpiles.py','stockpile-live-validation.json'),
       'chat-visibility':('chatVisibility','verify_chat_visibility.py','chat-visibility-validation.json'),
       'chat-background':('chatBackground','verify_chat_background.py','chat-background-validation.json'),
       'layout-notices':('chatBackground','verify_native_chat_notices.py','native-chat-notices-validation.json'),
       'layout-recovery':('chatBackground','verify_native_chat_recovery.py','native-chat-recovery-validation.json'),
       'layout-background':('chatBackground','verify_native_chat_background.py','native-chat-background-validation.json'),
       'blueprint-chat':('chatBackground','verify_blueprint_coordinator.py','blueprint-coordinator-validation.json'),
       'viewport':('viewport','verify_viewport.py','viewport-validation.json'),
       'ground-moisture':('groundMoisture','verify_ground_moisture.py','ground-moisture-validation.json'),
       'tiles':('tiles','verify_tiles.py','tile-capture-validation.json'),
       'entities':('capture','verify_entity_captures.py','capture-validation.json'),
       'world-lists':('worldLists','verify_world_lists.py','world-list-validation.json'),
       'faction-ui':('factionUi','verify_faction_ui.py','faction-ui-validation.json'),
       'regional-output':('regionalOutput','verify_regional_output_readers.py','regional-output-reader-validation.json'),
       'regional-output-export':('regionalExport','verify_regional_output_export.py','regional-output-validation.json'),
       'regional-capture':('regionalCapture','verify_regional_captures.py','regional-capture-validation.json'),
       'regional-cost':('regionalCost','verify_regional_cost.py','regional-cost-validation.json'),
       'regional-live':('regionalLive','verify_live_regional.py','regional-live-validation.json')}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def layout_preferences_directory(case, directory, runtime):
    """Fixed restart-fixture seam; never accept a normal profile/configuration root."""
    if directory is None:
        return None
    if case != 'layout-background':
        raise ValueError('Explicit preferences are only supported by the fixed layout background fixture')
    root = Path(runtime).resolve(strict=True)
    requested = Path(directory).absolute()
    real = requested.resolve(strict=True)
    if real != requested or real == root or not real.is_relative_to(root) or not real.is_dir():
        raise ValueError('Preferences require a regular private directory below runtime')
    info = real.stat()
    if stat.S_IMODE(info.st_mode) != 0o700 or info.st_uid != os.getuid():
        raise ValueError('Preferences directory must be caller-owned and mode 0700')
    return real


def layout_shared_state_directory(case, directory, runtime):
    """Internal automatic-restart seam: only an empty/prefs-only owned fixture root."""
    root = layout_preferences_directory(case, directory, runtime)
    if root is None:
        return None
    with os.scandir(root) as entries:
        for entry in entries:
            if entry.name != 'chat-layout.preferences' or entry.is_symlink() or not entry.is_file(follow_symlinks=False):
                raise ValueError('Shared fixture state must be empty or contain only regular preferences')
            info = entry.stat(follow_symlinks=False)
            if stat.S_IMODE(info.st_mode) != 0o600 or info.st_uid != os.getuid():
                raise ValueError('Shared preferences must be caller-owned and mode 0600')
    return root


def run(args):
    env_file=getattr(args,'env_file',None)
    if env_file is not None and args.case!='tiles':
        raise ValueError('--env-file is only supported by the explicit paid tiles handoff check')
    manifest=check(ROOT,args.candidate_dir,args.validation)
    runtime=(ROOT/'runtime').resolve();home=runtime/'smoke-home';save=args.save.resolve()
    if home.is_symlink() or not home.is_dir() or not save.is_file() or not save.is_relative_to(runtime):
        raise ValueError('Use isolated smoke-home and a copied save under runtime/')
    preferences=layout_preferences_directory(args.case,getattr(args,'layout_preferences_dir',None),runtime)
    game=args.game_dir.resolve();jdk=args.jdk_home.resolve();java=args.java.resolve()
    audit=json.loads((ROOT/'api-audit.json').read_text())
    for key,path in [('game_jar_sha256',game/'SongsOfSyx.jar'),('source_archive_sha256',game/'info/SongsOfSyx-sources.jar')]:
        if sha(path)!=audit[key]:raise ValueError('Game/source differs from current public API audit')
    if args.case in {'regional-output','regional-output-export'}:
        review=json.loads((ROOT/'REGIONAL_OUTPUT_BOUNDARY_REVIEW.json').read_text())
        if not review['passed'] or any(review[k]!=audit[k] for k in ('game_jar_sha256','source_archive_sha256')):
            raise ValueError('Regional-output candidate requires a passing paired static review')
    if args.case=='world-lists':
        review=json.loads((ROOT/'WORLD_LIST_BOUNDARY_REVIEW.json').read_text())
        if not review['passed'] or any(review[k]!=audit[k] for k in ('game_jar_sha256','source_archive_sha256')) or review['verifier_source_sha256']!=sha(ROOT/'dev/review_world_list_boundary.py'):
            raise ValueError('World-list context requires passing paired current static review')
    if args.case=='ground-moisture':
        review=json.loads((ROOT/'GROUND_MOISTURE_BOUNDARY_REVIEW.json').read_text())
        if not review['passed'] or any(review[k]!=audit[k] for k in ('game_jar_sha256','source_archive_sha256')) or review['verifier_source_sha256']!=sha(ROOT/'dev/review_ground_moisture.py'):
            raise ValueError('Ground moisture requires passing paired current candidate review')
    if args.case=='viewport':
        review=json.loads((ROOT/'VIEWPORT_BOUNDARY_REVIEW.json').read_text())
        if not review['passed'] or any(review[k]!=audit[k] for k in ('game_jar_sha256','source_archive_sha256')) or review['verifier_source_sha256']!=sha(ROOT/'dev/review_viewport_boundary.py'):
            raise ValueError('Viewport candidate requires passing paired current source review')
    shared_state=layout_shared_state_directory(args.case,getattr(args,'layout_shared_state_dir',None),runtime)
    if shared_state is not None and preferences is not None:
        raise ValueError('Automatic shared-state fixture cannot override the preference directory')
    state=shared_state or Path(tempfile.mkdtemp(prefix='read-'+args.case+'-',dir=runtime));os.chmod(state,0o700)
    jar=state/'syx-ai-assistant.jar'
    with zipfile.ZipFile((args.candidate_dir or ROOT/'releases')/'latest-user-test.zip') as z:
        jar.write_bytes(z.read('mod/syx-ai-assistant/V71/script/syx-ai-assistant.jar'))
    assert sha(jar)==manifest['mod_jar_sha256']
    classes=state/'classes';classes.mkdir()
    env=native_environment(os.environ);env['PYTHONPATH']=str(ROOT)
    sources=sorted((ROOT/'mod/tests').glob('*.java'))
    overlay_sources=[]
    if args.case in {'layout-background','layout-recovery','layout-notices'}:
        candidate=ROOT/'dev/candidates/chat-layout'
        overlay_sources=[candidate/'ChatPanel.java',candidate/'ChatBackgroundScenario.java',
            ROOT/'dev/java/syx/assistant/candidate/GestureReducer.java',ROOT/'dev/java/syx/assistant/candidate/PanelPreferences.java',ROOT/'dev/java/syx/assistant/candidate/PanelTheme.java',ROOT/'dev/java/syx/assistant/candidate/StatusLines.java']
        sources=[p for p in sources if p.name!='ChatBackgroundScenario.java']+overlay_sources
    frozen_sources={str(p.relative_to(ROOT)):sha(p) for p in sources+[ROOT/'dev/run_read_fixture.py',ROOT/'dev/verify_native_chat_background.py']} if overlay_sources else {}
    subprocess.run(['java','-Djava.home='+str(jdk),'-m','jdk.compiler/com.sun.tools.javac.Main',
        '--release','16','-encoding','UTF-8','-cp',str(game/'SongsOfSyx.jar')+os.pathsep+str(jar),'-d',str(classes),
        *map(str,sources)],env=env,check=True)
    target=home/'.local/share/songsofsyx/mods/syx-ai-assistant/V71/script/syx-ai-assistant.jar'
    if target.is_symlink() or not target.is_file() or not target.resolve().is_relative_to(home.resolve()):
        raise ValueError('Copied-profile mod JAR must be regular and stay inside smoke-home')
    backup=state/'prior-mod.jar';shutil.copy2(target,backup);save_before=sha(save)
    flag,verifier,report_name=CASES[args.case]
    # Fixed own-class overlay only for the explicit developer case. Licensed
    # engine/tutorial classes retain precedence; no caller-supplied class paths.
    own_classes=[classes,jar] if overlay_sources else [jar,classes]
    cp=os.pathsep.join(map(str,[game/'SongsOfSyx.jar',game/'base/script/000_Tutorial.jar',game/'base/script/001_Tutorial.jar',*own_classes]))
    command=[str(java),'-Xmx4g','-Duser.home='+str(home),'-Dsyx.assistant.stateDir='+str(state),
        '-Dsyx.smoke.'+flag+'=true','-cp',cp,'LiveSmoke',str(save)]
    if args.case in {'layout-recovery','layout-notices'}:command.insert(1,'-Dsyx.smoke.chatRecovery=true')
    if args.case=='layout-notices':command.insert(1,'-Dsyx.smoke.chatNotices=true')
    if preferences is not None:command.insert(1,'-Dsyx.assistant.candidate.preferencesDirectory='+str(preferences))
    if env_file is not None:command.insert(1,'-Dsyx.smoke.targetDispatchPro=true')
    process=None
    try:
        shutil.copy2(jar,target)
        subprocess.run([*command[:-2],'-Dsyx.smoke.validateOnly=true',*command[-2:]],cwd=game,env=env,check=True)
        with (state/'game.log').open('w') as game_log,(state/'verifier.log').open('w') as verify_log:
            process=subprocess.Popen(command,cwd=game,env=env,stdout=game_log,stderr=subprocess.STDOUT)
            verifier_args=[sys.executable,str(ROOT/'dev'/verifier),'--state-dir',str(state)]
            if env_file is not None:verifier_args+=['--env-file',str(env_file.resolve())]
            subprocess.run(verifier_args,cwd=ROOT,env=env,
                stdout=verify_log,stderr=subprocess.STDOUT,check=True,timeout=660 if env_file is not None else 330)
            process.wait(timeout=30);assert process.returncode==0
        require_clean_game_log(state/'game.log')
        report=json.loads((state/report_name).read_text());assert report['passed']
        report['known_engine_crash_markers_absent']=True
        if args.case=='stockpile-matrix':
            completion=json.loads((state/'stockpile-matrix-clean-exit.json').read_text())
            if completion!={'passed':True,'verified_phases':2}:
                raise RuntimeError('Warehouse matrix fixture did not confirm clean completion')
            report['explicit_fixture_clean_completion']=True
        if args.case=='stockpile-lifecycle':
            completion=json.loads((state/'stockpile-lifecycle-clean-exit.json').read_text())
            if completion!={'passed':True,'verified_phases':3}:
                raise RuntimeError('Warehouse lifecycle fixture did not confirm clean completion')
            report['explicit_fixture_clean_completion']=True
        if args.case=='world-lists':
            completion=json.loads((state/'world-list-clean-exit.json').read_text())
            if not completion.get('passed') or completion.get('verified_phases')!=14 or (state/'world-list-fixture-failure.json').exists():
                raise RuntimeError('World-list fixture did not confirm clean completion')
            report['explicit_fixture_clean_completion']=True
        if args.case=='ground-moisture':
            completion=json.loads((state/'ground-moisture-clean-exit.json').read_text())
            if completion!={'passed':True,'samples':64} or (state/'ground-moisture-fixture-failure.json').exists():
                raise RuntimeError('Ground-moisture candidate fixture did not confirm clean completion')
            report['explicit_fixture_clean_completion']=True
        if args.case=='viewport':
            completion=json.loads((state/'viewport-clean-exit.json').read_text())
            if completion!={'passed':True,'verified_phases':11} or (state/'viewport-fixture-failure.json').exists():
                raise RuntimeError('Viewport candidate fixture did not confirm clean completion')
            report['explicit_fixture_clean_completion']=True
        if args.case in {'layout-background','layout-recovery','layout-notices'}:
            completion=json.loads((state/'layout-background-clean-exit.json').read_text())
            if completion!={'passed':True,'verified_phases':11 if args.case=='layout-notices' else 9 if args.case=='layout-recovery' else 7} or (state/'layout-background-fixture-failure.json').exists():
                raise RuntimeError('Native layout background fixture did not confirm clean completion')
            if frozen_sources!={n:sha(ROOT/n) for n in frozen_sources}:
                raise RuntimeError('Native layout overlay source changed during fixture')
            report.update(explicit_fixture_clean_completion=True,our_chat_class_overlaid_from_fixture_classes=True,
                engine_classes_overridden=False,compiled_fixture_source_sha256=frozen_sources,
                compiled_overlay_class_sha256_collected_after_native_exit={str(p.relative_to(classes)):sha(p) for p in sorted(classes.rglob('*.class'))
                    if str(p.relative_to(classes)).startswith(('syx/assistant/ChatPanel','syx/assistant/ChatBackgroundScenario','syx/assistant/candidate/GestureReducer','syx/assistant/candidate/PanelPreferences','syx/assistant/candidate/PanelTheme'))})
        if args.case in {'chat-background','blueprint-chat'}:
            completion=json.loads((state/'chat-background-clean-exit.json').read_text())
            if completion!={'passed':True,'verified_phases':3} or (state/'chat-background-fixture-failure.json').exists():
                raise RuntimeError('Background chat fixture did not confirm clean completion')
            report['explicit_fixture_clean_completion']=True
        if args.case=='chat-visibility':
            completion=json.loads((state/'chat-visibility-clean-exit.json').read_text())
            if completion!={'passed':True,'verified_phases':3} or (state/'chat-visibility-fixture-failure.json').exists():
                raise RuntimeError('Chat visibility probe did not confirm clean completion')
            report['explicit_fixture_clean_completion']=True
        report.update(validated_at=datetime.now(timezone.utc).isoformat(),game_exit_code=process.returncode,
            mod_jar_sha256=sha(jar),game_jar_sha256=audit['game_jar_sha256'],
            source_archive_sha256=audit['source_archive_sha256'],
            production_source_sha256=manifest['validation']['production_source_sha256'],
            python_source_sha256=manifest['validation']['python_source_sha256'],inference_calls=report.get('inference_calls',0))
        report['fixture_source_sha256']={n:sha(ROOT/n) for n in ['mod/tests/LiveSmoke.java','mod/tests/WeatherScenario.java','mod/tests/StockpileMatrixScenario.java','mod/tests/StockpileLifecycleScenario.java','mod/tests/TileScenario.java',
            'mod/tests/EntityScenario.java','mod/tests/SceneScenario.java','mod/tests/FactionUiScenario.java','mod/tests/RegionalOutputScenario.java','mod/tests/RegionalOutputExportScenario.java','mod/tests/RegionalLiveScenario.java','mod/tests/RegionalCostScenario.java','mod/tests/RegionalCaptureScenario.java','mod/tests/WorldListScenario.java','mod/tests/GroundMoistureScenario.java','mod/tests/ViewportScenario.java','mod/tests/ChatBackgroundScenario.java','mod/tests/ChatVisibilityScenario.java','dev/'+verifier,'dev/run_read_fixture.py','dev/native_game_completion.py']}
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        shutil.copy2(backup,target)
        if sha(target)!=sha(backup) or sha(save)!=save_before:
            raise RuntimeError('Copied mod restoration/save integrity check failed; no passing final report written')
    if args.case=='world-lists':
        report['boundary_review_sha256']=sha(ROOT/'WORLD_LIST_BOUNDARY_REVIEW.json')
    if args.case=='viewport':
        report['candidate_boundary_review_sha256']=sha(ROOT/'VIEWPORT_BOUNDARY_REVIEW.json')
    if args.case=='ground-moisture':
        report['candidate_boundary_review_sha256']=sha(ROOT/'GROUND_MOISTURE_BOUNDARY_REVIEW.json')
    if args.case in {'regional-live','regional-capture'}:
        report['fixture_source_sha256']['dev/regional_partial_cache_server.py']=sha(ROOT/'dev/regional_partial_cache_server.py')
        report['fixture_source_sha256']['dev/verify_scenes.py']=sha(ROOT/'dev/verify_scenes.py')
    if args.case in {'regional-output','regional-output-export'}:
        report['candidate_boundary_review_sha256']=sha(ROOT/'REGIONAL_OUTPUT_BOUNDARY_REVIEW.json')
    if env_file is not None:
        report['fixture_source_sha256']['dev/verify_target_dispatch_pro.py']=sha(ROOT/'dev/verify_target_dispatch_pro.py')
    report.update(copied_profile_mod_restored=True,copied_save_unchanged=True)
    output=state/'read-validation.json';output.write_text(json.dumps(report,indent=2)+'\n')
    print('Read fixture passed:',output)
    return output


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case',choices=CASES,required=True)
    for name in ('game-dir','jdk-home','java','save'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--candidate-dir',type=Path);p.add_argument('--validation',type=Path)
    p.add_argument('--env-file',type=Path,help='Explicit paid tiles-only Pro handoff check; never passed to the game or MCP')
    args=p.parse_args()
    with exclusive_fixture():run(args)
