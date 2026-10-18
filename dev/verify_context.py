"""Validate exported snapshots from the isolated ContextScenario; never drives UI itself."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import time
from syx_mcp import Advisor


def verify(directory: Path, timeout: float = 220):
    advisor=Advisor(directory/'snapshot.json',directory/'corpus.json')
    checked={}
    first_session=None
    start=time.monotonic()
    required={'settlement','subject','game_menu','confirmation','world','management','encyclopedia','loading_overlay','room','reloaded','main_menu'}
    while time.monotonic()-start<timeout:
        try:
            phase=json.loads((directory/'phase.json').read_text())
            name=phase['phase']
            age=(datetime.now(timezone.utc)-datetime.fromisoformat(phase['started_at'].replace('Z','+00:00'))).total_seconds()
            if name in checked or age<3:
                time.sleep(.3);continue
            snapshot=advisor.snapshot();status=advisor.status(snapshot)
            if first_session is None:first_session=snapshot.session_id
            context=snapshot.ui_context;flags=context.get('known_overlays',{})
            if name=='main_menu':
                if age<32:time.sleep(.3);continue
                assert not status['live'] and status['game_loaded'] is None
                assert status['state_certainty']=='unknown_updates_stopped'
            else:
                if name=='reloading':time.sleep(.3);continue
                assert status['live'],status
                assert context.get('available'),context
                assert context['coverage']=='partial' and not context['overlay_order_known']
                assert context['unsupported']['selected_room_instance']
                if name=='settlement':assert context['active_view']=='settlement'
                if name=='subject':
                    selected=snapshot.domains['entities'].data['selected_subject']
                    assert selected is not None
                    assert selected['entity_id']==context['selected_subject']['entity_id']
                    assert selected['stats'] and all(row['reference_id'].startswith('stat:') for row in selected['stats'])
                    assert any(row['coverage']=='partial' and type(row['value']) is int for row in selected['stats'])
                    spec={'queries':[{'source':{'domain':'entities','path':'/selected_subject/stats'},
                        'where':{'eq':[{'field':'/coverage'},'partial']},
                        'select':{'stat_id':{'field':'/stat_id'},'value':{'field':'/value'},'reference_id':{'field':'/reference_id'}},'limit':5}],
                        'include_ui_context':True,'expected_snapshot_id':snapshot.snapshot_id}
                    chosen=advisor.select(spec)
                    assert chosen['state']['snapshot_id']==snapshot.snapshot_id
                    assert chosen['ui_context']['selected_subject']['entity_id']==selected['entity_id']
                    assert chosen['results'][0]['rows']
                    print('INDIVIDUAL_STATS',len(selected['stats']),'ENTITY_TOTAL',snapshot.domains['entities'].data['total'],flush=True)
                if name=='game_menu':assert flags['game_menu'] and context['known_overlay_active']
                if name=='confirmation':assert flags['confirmation'] and not flags['game_menu']
                if name=='world':assert context['active_view']=='world' and context['selected_subject'] is None
                if name=='management':assert flags['management_screen']
                if name=='encyclopedia':assert flags['encyclopedia'] and not flags['management_screen']
                if name=='loading_overlay':assert flags['loading']
                if name=='room':
                    assert context['open_room_blueprints'] and context['selected_subject'] is None
                    catalog={r.id:r for r in snapshot.references}
                    for room in context['open_room_blueprints']:
                        assert room['reference_id']=='room:'+room['blueprint_id']
                        assert catalog[room['reference_id']].category=='room'
                if name=='reloaded':assert snapshot.session_id!=first_session and context['active_view']=='settlement'
            checked[name]={'passed':True,'snapshot_fresh':status['fresh'],'ui_context_available':bool(context.get('available')) if name!='main_menu' else False}
            print('PASS',name,flush=True)
            if required<=checked.keys():break
        except (FileNotFoundError,json.JSONDecodeError):pass
        time.sleep(.3)
    missing=required-checked.keys()
    report={'passed':not missing,'checks':checked,'missing':sorted(missing),
        'limits':['Main menu is inferred only as unknown/stale after updates stop; no menu identification API established.',
                  'Room references identify blueprint help, not a selected instance or a complete tooltip.',
                  'Loading-overlay flag test is separate from the real save reload transition.',
                  'Battle, world generation and other menu subpages remain untested.']}
    (directory/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    if missing:raise AssertionError('Missing fixture phases: '+str(sorted(missing)))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True);p.add_argument('--timeout',type=float,default=220)
    args=p.parse_args();verify(args.state_dir,args.timeout)
