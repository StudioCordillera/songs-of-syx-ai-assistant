"""Validate candidate public stockpile readers and existing MCP totals in a copied city.

No production mapping change, provider request, input automation, save, screenshot or
normal-profile access. Run under an isolated virtual display to leave a player alone.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from check_user_test_release import check
from game_fixture_lock import exclusive_fixture
from run_player_chat_check import native_environment


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def check_game_pair(game,review_path=ROOT/'STOCKPILE_BOUNDARY_REVIEW.json'):
    review=json.loads(review_path.read_text())
    pair={'game_jar_sha256':sha(game/'SongsOfSyx.jar'),
          'source_archive_sha256':sha(game/'info/SongsOfSyx-sources.jar')}
    if not review.get('passed') or any(review.get(k)!=v for k,v in pair.items()):
        raise ValueError('Licensed game/source differs from the static stockpile review; re-establish the candidate contract')
    return {**pair,'static_boundary_review_sha256':sha(review_path)}


async def verify(state,manifest):
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    from syx_mcp import Snapshot
    fixture=json.loads((state/'stockpile-fixture.json').read_text())
    snapshot=Snapshot.model_validate_json((state/'stockpile-observation.json').read_bytes())
    assert fixture['passed'] and snapshot.game_loaded and not snapshot.demo
    assert snapshot.scene['settlement_scene_kind']=='city'
    expected={r['resource_id']:r for r in fixture['totals']}
    # Check the actual current production mapping, not a test-only invented domain.
    observed=snapshot.domains['resources'].data['stockpiles']
    assert len(observed)==len(expected)==fixture['resource_count']
    for row in observed:
        direct=expected[row['id']]
        assert row['stockpile_stored']==direct['amount']
        assert row['stockpile_capacity']==direct['space']
    # Serve the real retained observation with its original timestamp in a separate directory.
    # It is never substituted into the live mod's snapshot mailbox.
    offline=state/'retained-observation';offline.mkdir(mode=0o700)
    shutil.copy2(state/'stockpile-observation.json',offline/'snapshot.json')
    env=native_environment(os.environ);env['SYX_STATE_DIR']=str(offline)
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(ROOT),env=env)
    source={'domain':'resources','path':'/stockpiles'}
    spec={'queries':[{'source':source,'where':{'gt':[{'field':'/stockpile_capacity'},0]},
        'select':{'resource':{'field':'/id'},'stored':{'field':'/stockpile_stored'},'capacity':{'field':'/stockpile_capacity'}},
        'sort':[{'field':'/stored','direction':'desc'}],'limit':5}], 'include_ui_context':True}
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            response=await session.call_tool('select_game_state',{'spec':spec})
            text=next(c.text for c in response.content if c.type=='text')
            assert not response.is_error,text
            result=json.loads(text);assert len(text.encode())<=65536
            rows=sorted([{'resource':r['resource_id'],'stored':r['amount'],'capacity':r['space']}
                for r in expected.values() if r['space']>0],key=lambda r:r['stored'],reverse=True)
            assert rows and result['results'][0]['rows']==rows[:5]
            assert result['results'][0]['matched_total']==len(rows)
            assert result['state']['session_id']==snapshot.session_id
            assert result['ui_context']==snapshot.ui_context
    metadata={k:fixture[k] for k in ['resource_count','room_count','active_rooms','inactive_rooms',
        'zero_capacity_resources','zero_capacity_aggregate_rooms','zero_capacity_room_resource_pairs','positive_tallies','assigned_crates',
        'total_crates','overload_comparisons','per_room_sum_global_parity','resource_zero_denominator_default_one',
        'controlled_inactive_room_stored_tallies_unchanged','controlled_reactivation_restored']}
    return {'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),
        'stage':'Candidate runtime reader review; existing production totals/MCP selection parity only.',
        'game_version':snapshot.game_version,'mod_jar_sha256':manifest['mod_jar_sha256'],
        'production_source_sha256':manifest['validation']['production_source_sha256'],
        'python_source_sha256':manifest['validation']['python_source_sha256'],
        'observed_at':snapshot.captured_at.isoformat(),
        'private_observation_sha256':sha(state/'stockpile-observation.json'),
        'private_getter_fixture_sha256':sha(state/'stockpile-fixture.json'),
        'native_checks':metadata,'existing_stored_capacity_getter_and_mcp_selection_parity':True,
        'original_observation_time_and_ui_context':True,'provider_calls':0,'save_writes':0,
        'controlled_public_actions':['RoomInstance.deactivate()','RoomInstance.activate(true)'],
        'action_scope':'Test-only copied room, after baseline observation; no production control route.',
        'source_sha256':{n:sha(ROOT/n) for n in ['mod/tests/StockpileScenario.java','mod/tests/LiveSmoke.java','dev/run_stockpile_probe.py']},
        'limits':['One paused copied city; no new reservation/per-room fields are exposed in the production DTO or MCP schema.',
            'Existing stored/capacity rows are tested through actual MCP over the retained real observation; candidate reservation/per-room arrays are compared inside the native fixture only.',
            'Resource and integer overload agreement and per-room/global sums are consistency checks, not an independent physical crate audit.',
            'Positive/zero baseline counts are measured, not synthesized. An empty room aggregate zero-capacity branch is unexecuted when zero_capacity_aggregate_rooms is zero.',
            'Only immediate deactivate/reactivate is tested on one copied room, after the baseline observation. No room removal, simulation over inactive periods, controlled reservation actions, battle/setup acceptance, cap/fault injection, large-city cost or full warehouse/logistics coverage.',
            'No screenshot, native input or normal game/profile manipulation. Use a separate virtual display with software rendering to isolate presentation while a normal player is running.']}


def run(args):
    manifest=check();runtime=(ROOT/'runtime').resolve();home=runtime/'smoke-home';save=args.save.resolve()
    if home.is_symlink() or not home.is_dir() or not save.is_file() or not save.is_relative_to(runtime):
        raise ValueError('Use the isolated smoke-home and a copied save under runtime/')
    if not os.environ.get('DISPLAY'):raise ValueError('A native display or isolated xvfb-run display is required')
    game=args.game_dir.resolve();jdk=args.jdk_home.resolve();java=args.java.resolve()
    pair=check_game_pair(game)
    state=Path(tempfile.mkdtemp(prefix='stockpile-probe-',dir=runtime));os.chmod(state,0o700)
    jar=state/'syx-ai-assistant.jar'
    with zipfile.ZipFile(ROOT/'releases/latest-user-test.zip') as z:
        jar.write_bytes(z.read('mod/syx-ai-assistant/V71/script/syx-ai-assistant.jar'))
    assert sha(jar)==manifest['mod_jar_sha256']
    classes=state/'classes';classes.mkdir()
    env=native_environment(os.environ);env['PYTHONPATH']=str(ROOT)
    subprocess.run(['java','-Djava.home='+str(jdk),'-m','jdk.compiler/com.sun.tools.javac.Main',
        '--release','16','-encoding','UTF-8','-cp',str(game/'SongsOfSyx.jar')+os.pathsep+str(jar),'-d',str(classes),
        *map(str,(ROOT/'mod/tests').glob('*.java'))],env=env,check=True)
    target=home/'.local/share/songsofsyx/mods/syx-ai-assistant/V71/script/syx-ai-assistant.jar'
    if target.is_symlink() or not target.is_file() or not target.resolve().is_relative_to(home.resolve()):
        raise ValueError('Copied-profile mod JAR must be regular and stay inside smoke-home')
    backup=state/'prior-mod.jar';shutil.copy2(target,backup)
    save_before=sha(save)
    cp=os.pathsep.join(map(str,[game/'SongsOfSyx.jar',game/'base/script/000_Tutorial.jar',game/'base/script/001_Tutorial.jar',jar,classes]))
    command=[str(java),'-Xmx4g','-Duser.home='+str(home),'-Dsyx.assistant.stateDir='+str(state),
        '-Dsyx.smoke.stockpile=true','-cp',cp,'LiveSmoke',str(save)]
    process=None
    try:
        shutil.copy2(jar,target)
        subprocess.run([*command[:-2],'-Dsyx.smoke.validateOnly=true',*command[-2:]],cwd=game,env=env,check=True)
        with (state/'game.log').open('w') as log:
            process=subprocess.Popen(command,cwd=game,env=env,stdout=log,stderr=subprocess.STDOUT)
            deadline=time.monotonic()+100
            while not (state/'stockpile-fixture.json').is_file():
                if process.poll() is not None:raise RuntimeError('Native stockpile probe exited early; see private log '+str(state/'game.log'))
                if time.monotonic()>deadline:raise RuntimeError('Native stockpile probe timed out; see private log '+str(state/'game.log'))
                time.sleep(.2)
            report=asyncio.run(verify(state,manifest))
            (state/'verifier.done').write_text('passed\n');process.wait(timeout=30)
            assert process.returncode==0
        report['game_exit_code']=process.returncode
        report.update(pair)
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        shutil.copy2(backup,target)
        if sha(target)!=sha(backup) or sha(save)!=save_before:
            raise RuntimeError('Copied profile restoration/save integrity check failed; no passing report written')
    report['copied_profile_mod_restored']=True
    report['copied_save_unchanged']=True
    output=state/'stockpile-probe-validation.json';output.write_text(json.dumps(report,indent=2)+'\n')
    print('Stockpile candidate probe passed:',output)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('game-dir','jdk-home','java','save'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    with exclusive_fixture():run(args)
