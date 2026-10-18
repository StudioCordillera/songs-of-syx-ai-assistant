"""Read exported snapshots during SceneScenario; no UI/process control."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import time
from syx_mcp import Advisor


def verify(directory:Path,timeout:float=260,on_demand:bool=False,tiles:bool=False):
    advisor=Advisor(directory/'snapshot.json',directory/'corpus.json')
    required={'city','settlement_battle','city_restored','battle_deployment','battle_menu','city_reloaded','world_generation','terrain_generated'}
    checks={};sessions={};began=time.monotonic()
    while time.monotonic()-began<timeout:
        try:
            phase=json.loads((directory/'phase.json').read_text());name=phase['phase']
            age=(datetime.now(timezone.utc)-datetime.fromisoformat(phase['started_at'].replace('Z','+00:00'))).total_seconds()
            if name not in required or name in checks or age<3:time.sleep(.25);continue
            snapshot=advisor.snapshot();status=advisor.status(snapshot);context=snapshot.ui_context;scene=snapshot.scene
            assert status['live'],status
            assert context.get('available'),context
            assert scene['active_view']==context['active_view']
            sessions[name]=snapshot.session_id
            if name in {'city','city_restored','city_reloaded'}:
                assert context['active_view']=='settlement'
                assert scene['settlement_exists'] and scene['settlement_scene_kind']=='city'
                assert snapshot.domains['population'].coverage=='partial'
                assert snapshot.domains['resources'].scope=='mixed_scene_logistics_and_player_trade_promises'
                assert snapshot.domains['resources'].data['field_definitions']['owned']['scope']=='mixed_scene_logistics_and_player_trade_promises'
                assert snapshot.domains['resources'].data['field_definitions']['stockpile_stored']['scope']=='instantiated_settlement_scene'
                assert snapshot.domains['trade'].scope=='campaign_player_or_faction'
                if name=='city_reloaded':assert snapshot.session_id!=sessions['city']
            if name=='settlement_battle':
                assert context['active_view']=='settlement_battle'
                assert scene['settlement_scene_kind']=='city'
            if name in {'battle_deployment','battle_menu'}:
                assert context['active_view']=='battle' and scene['settlement_scene_kind']=='battlefield'
                battle=context['battle_context']
                assert battle['available'] and battle['deploying']
                assert battle['player_men']==10 and battle['enemy_men']==10,battle
                assert battle['deployment_bounds']['unit']=='settlement_tiles'
                if name=='battle_menu':assert context['known_overlays']['game_menu']
            if name in {'world_generation','terrain_generated'}:
                assert context['active_view']=='world_generation',context
                assert not scene['settlement_exists'] and scene['settlement_scene_kind']=='unavailable',scene
                assert not scene['world_generation']['is_done']
                assert snapshot.session_id!=sessions['city_reloaded']
                for domain in snapshot.domains.values():
                    # The only meaningful runtime data during empty game setup is the clock/settings.
                    if domain is snapshot.domains['settings']:continue
                    assert domain.coverage=='unavailable' and domain.data is None,domain
                assert scene['world_generation']['has_generated_terrain']==(name=='terrain_generated')
                assert not context['world_generation_step']['available']
            production=snapshot.domains['production']
            if name not in {'world_generation','terrain_generated'}:
                assert production.coverage=='partial',production.reason
                assert production.scope=='mixed_scene_production_and_campaign_ledger'
                assert production.data['room_data']['coverage']=='partial'
                assert production.data['room_data']['scope']=='instantiated_settlement_scene'
                assert production.data['room_data']['failed_rooms']==0
            read_available=None
            if on_demand:
                from syx_live import query_entities
                if name in {'world_generation','terrain_generated'}:
                    try:query_entities(advisor,{'fields':['id'],'limit':1,'expected_session_id':snapshot.session_id})
                    except ValueError as error:assert 'No instantiated settlement scene' in str(error),error
                    else:raise AssertionError('Empty world setup must reject entity reads')
                    read_available=False
                else:
                    observation=query_entities(advisor,{'fields':['id'],'limit':1,'expected_session_id':snapshot.session_id})
                    assert observation['scene']['settlement_scene_kind']==scene['settlement_scene_kind']
                    assert observation['ui_context']['active_view']==context['active_view']
                    read_available=True
            tile_available=None
            if tiles:
                from syx_tiles import query_tiles
                selection={'tile_bounds':[0,0,1,1],'fields':['terrain','floor','room','minerals','path'],
                           'limit':1,'expected_session_id':snapshot.session_id}
                if name in {'world_generation','terrain_generated'}:
                    try:query_tiles(advisor,selection)
                    except ValueError as error:assert 'No instantiated settlement scene' in str(error),error
                    else:raise AssertionError('Empty world setup must reject tile reads')
                    tile_available=False
                else:
                    tile=query_tiles(advisor,selection)
                    assert tile['scene']['settlement_scene_kind']==scene['settlement_scene_kind']
                    assert tile['ui_context']['active_view']==context['active_view']
                    assert tile['data']['rows'][0]['terrain']['available']
                    assert tile['data']['next_cursor'] is None
                    tile_available=True
            checks[name]={'passed':True,'view':context['active_view'],'scene_kind':scene['settlement_scene_kind'],
                          'on_demand_read_available':read_available,'tile_read_available':tile_available,
                          'production_coverage':production.coverage,
                          'production_room_coverage':production.data['room_data']['coverage'] if production.data else 'unavailable'}
            print('PASS',name,flush=True)
            if required<=checks.keys():break
        except (FileNotFoundError,json.JSONDecodeError):pass
        time.sleep(.25)
    missing=required-checks.keys()
    report={'passed':not missing,'checks':checks,'missing':sorted(missing),
            'limits':['Battle is a generated deployment scene, not active fighting or a battle conclusion.',
                      'Generation checks initial setup and public terrain generation; exact private wizard step and full political-world completion remain unvalidated.']}
    (directory/'scene-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    if missing:raise AssertionError('Missing scene phases: '+str(sorted(missing)))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True);p.add_argument('--timeout',type=float,default=260)
    p.add_argument('--on-demand',action='store_true')
    p.add_argument('--tiles',action='store_true')
    args=p.parse_args();verify(args.state_dir,args.timeout,args.on_demand,args.tiles)
