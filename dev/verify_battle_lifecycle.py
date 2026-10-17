"""Observe BattleLifecycleScenario using exported data and read-only MCP calls."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import time
from syx_mcp import Advisor

def verify(directory:Path,timeout=450):
    advisor=Advisor(directory/'snapshot.json',directory/'corpus.json')
    required={'city','deployment_victory','engagement_victory','result_victory','after_victory',
              'deployment_defeat','engagement_defeat','result_defeat','after_defeat'}
    checks={};sessions={};began=time.monotonic()
    while time.monotonic()-began<timeout:
        try:
            phase=json.loads((directory/'phase.json').read_text());name=phase['phase']
            started=datetime.fromisoformat(phase['started_at'].replace('Z','+00:00'))
            if name not in required or name in checks or (datetime.now(timezone.utc)-started).total_seconds()<2.5:
                time.sleep(.15);continue
            snapshot=advisor.snapshot();status=advisor.status(snapshot);ui=snapshot.ui_context;scene=snapshot.scene
            if snapshot.captured_at<started:time.sleep(.15);continue
            assert status['live'] and ui['available'],status
            capture=ui['input_capture']
            assert type(capture['global_hover_consumed']) is bool and type(capture['active_view_hover_consumed']) is bool
            military=snapshot.domains['military'];assert military.coverage=='partial',military
            armies={a['side']:a for a in military.data['scene_armies']}
            assert all('remain stale' in a['status_note'] for a in armies.values())
            if name.startswith(('deployment_','engagement_','result_')):
                assert ui['active_view']=='battle' and scene['settlement_scene_kind']=='battlefield'
                assert 'private' in ui['unsupported']['battle_conclusion_overlay']
                if name.startswith('deployment_'):
                    assert ui['battle_context']['deploying']
                    assert armies['player']['men']==armies['enemy']['men']==40
                else:assert not ui['battle_context']['deploying']
                if name.startswith('engagement_'):
                    assert phase['engagement_seen']
                    assert any(d.get('engine_engagement_flag') for a in armies.values() for d in a['divisions']),armies
                    assert snapshot.domains['settings'].data['speed_target']>=1
                if name.startswith('result_'):
                    assert armies['enemy' if name.endswith('victory') else 'player']['men']==0
                    assert capture['global_hover_consumed']
                    assert capture['global_hover_consumed_without_known_overlay_flag']
                    # No fabricated result-dialog identity or text may appear in the production context.
                    assert not ui['known_overlay_active'] and not ui['known_content']['roots']
            if name.startswith('after_'):
                assert ui['active_view']=='settlement' and scene['settlement_scene_kind']=='city'
                assert snapshot.session_id!=sessions['deployment_'+name.split('_',1)[1]]
            sessions[name]=snapshot.session_id
            checks[name]={'passed':True,'view':ui['active_view'],'player_men':armies['player']['men'],'enemy_men':armies['enemy']['men'],
                          'engine_engagement_observed':any(d.get('engine_engagement_flag') for a in armies.values() for d in a['divisions']),
                          'global_hover_consumed':capture['global_hover_consumed']}
            print('PASS',name,flush=True)
            if required<=checks.keys():break
        except (FileNotFoundError,json.JSONDecodeError):pass
        time.sleep(.15)
    missing=required-checks.keys()
    report={'passed':not missing,'checks':checks,'missing':sorted(missing),
        'limits':['Start/result Close dispatch is test-only through public game managers; no OS/native input or screenshots.',
                  'Genuine engine engagement is observed before deterministic public casualty setup. Victory/defeat are controlled fixture outcomes, not AI combat benchmarks.',
                  'Actual private result overlays are not inspected. The test-supplied exiter verifies outcomes; production exposes no result-dialog identity or arbitrary outcome event feed.',
                  'DivStatus is the latest published battle-worker buffer and may lag or miss brief engagement; not a complete combat log.']}
    (directory/'battle-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    if missing:raise AssertionError('Missing fixture phases: '+str(sorted(missing)))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True)
    verify(p.parse_args().state_dir)
