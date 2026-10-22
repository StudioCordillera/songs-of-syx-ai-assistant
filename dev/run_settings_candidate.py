"""Fixed source-reviewed configured-settings candidate in a disposable copied game."""
import argparse,hashlib,json,shutil,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from game_fixture_lock import exclusive_fixture
from run_stockpile_probe import run,sha

NAMES=('dev/run_settings_candidate.py','dev/review_settings_boundary.py',
       'dev/candidates/settings/StockpileScenario.java',
       'dev/candidates/settings/syx/assistant/candidate/SettingsObservation.java',
       'dev/run_stockpile_probe.py','mod/tests/LiveSmoke.java')
FROZEN={}

async def verify(state,manifest):
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    from syx_mcp import Snapshot
    fixture=json.loads((state/'stockpile-fixture.json').read_text())
    assert fixture['passed'] and fixture['fixed_settings']==16 and fixture['explicit_settings_mutations']==0 and not fixture['lazy_initialization_by_reader']
    assert [x['phase'] for x in fixture['checks']]==['city','world','city_return']
    assert [x['active_view'] for x in fixture['checks']]==['settlement','world','settlement']
    assert all(x['passed'] and x['getter_comparisons']==48 for x in fixture['checks'])
    raw=(state/'settings-observation.json').read_bytes();snapshot=Snapshot.model_validate_json(raw)
    assert snapshot.game_loaded and not snapshot.demo and snapshot.scene['settlement_scene_kind']=='city'
    options=snapshot.domains['settings'].data['configured_options']
    assert options['available'] and options['coverage']=='partial' and options['data']['complete_fixed_selection']
    assert options['data']['rows']==fixture['expected_rows'] and options['data']['failed_settings']==[]
    retained=state/'retained-observation';retained.mkdir(mode=0o700);shutil.copy2(state/'settings-observation.json',retained/'snapshot.json')
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(ROOT),env={'SYX_STATE_DIR':str(retained)})
    spec={'queries':[{'source':{'domain':'settings','path':'/configured_options/data/rows'},
        'select':{'id':{'field':'/setting_id'},'value':{'field':'/configured_steps'},'minimum':{'field':'/minimum_steps'},'maximum':{'field':'/maximum_steps'}},'limit':20},
        {'source':{'domain':'settings','path':'/configured_options/data'},
         'select':{'requested':{'field':'/requested_settings'},'complete':{'field':'/complete_fixed_selection'},'failures':{'field':'/failed_settings'}},'limit':1}], 'include_ui_context':True}
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            result=await session.call_tool('select_game_state',{'spec':spec})
            text=next(c.text for c in result.content if c.type=='text');assert not result.is_error,text
            selected=json.loads(text);expected=[{'id':r['setting_id'],'value':r['configured_steps'],'minimum':r['minimum_steps'],'maximum':r['maximum_steps']} for r in fixture['expected_rows']]
            assert selected['results'][0]['rows']==expected and selected['results'][0]['matched_total']==16
            assert selected['results'][1]['rows']==[{'requested':16,'complete':True,'failures':[]}]
            assert selected['state']['session_id']==snapshot.session_id and selected['ui_context']==snapshot.ui_context
            assert len(text.encode())<=65536
            definitions=await session.call_tool('describe_game_fields',{'domain':'settings'})
            assert not definitions.is_error and 'configured_steps' in str(definitions)
            calls=2
    assert FROZEN=={name:sha(ROOT/name) for name in NAMES}
    return {'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),
        'scope':'Developer fixed configured UI setting steps in a copied game: direct getter parity in city/world/return, then selective real MCP against a retained candidate-augmented native observation.',
        'native_checks':{k:v for k,v in fixture.items() if k!='expected_rows'},'candidate_packaged_in_player':False,
        'mcp_calls':calls,'selected_rows':16,'same_observation_context':True,'external_inference_calls':0,
        'source_sha256':FROZEN,'static_review_sha256':sha(ROOT/'SETTINGS_BOUNDARY_REVIEW.json'),
        'private_snapshot_sha256':hashlib.sha256(raw).hexdigest(),'mod_jar_sha256':manifest['mod_jar_sha256'],
        'compiled_candidate_sha256_collected_before_native_exit':{str(p.relative_to(state/'classes')):sha(p) for p in (state/'classes').rglob('SettingsObservation*.class')},
        'limits':['The production snapshot/MCP/player are unchanged. Candidate settings are added only to a separate retained fixture snapshot; no new tool or game setter.',
            'S was initialized by LiveSmoke before CORE creation. This does not establish a safe public first-initialization route for an observer or main-menu lifecycle.',
            'Reported values are configured UI steps. Quantized audio zero does not prove zero underlying gain, physical silence or OS mute.',
            'Three fixed own view phases, not all menus/scenes, focus state, actual audio/rendering, autosave ETA, native faults or worst-case performance.',
            'Test-only speed/view changes and engine background writes stay in the disposable copied profile; no explicit save requested.']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('game-dir','jdk-home','java','save'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--candidate-dir',type=Path);p.add_argument('--validation',type=Path)
    args=p.parse_args()
    review=json.loads((ROOT/'SETTINGS_BOUNDARY_REVIEW.json').read_text())
    if not review['passed'] or review['reviewer_source_sha256']!=sha(ROOT/'dev/review_settings_boundary.py'):raise ValueError('Current passing settings boundary review required')
    FROZEN={name:sha(ROOT/name) for name in NAMES}
    with exclusive_fixture():
        run(args,scenario_override=ROOT/'dev/candidates/settings/StockpileScenario.java',
            extra_sources=(ROOT/'dev/candidates/settings/syx/assistant/candidate/SettingsObservation.java',),
            verifier=verify,report_name='settings-candidate-validation.json',boundary_review_path=ROOT/'SETTINGS_BOUNDARY_REVIEW.json',
            completion_marker=('settings-clean-exit.json',{'passed':True,'verified_phases':3}))
