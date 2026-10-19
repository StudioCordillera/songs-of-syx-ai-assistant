"""Read exported snapshots during SceneScenario; no UI/process control."""
import argparse
import asyncio
import os
import sys
from datetime import datetime,timezone
import json
from pathlib import Path
import time
from syx_mcp import Advisor


async def unavailable_city_data_mcp(directory):
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    root=Path(__file__).resolve().parent.parent
    env={k:v for k,v in os.environ.items() if not any(t in k for t in ('API_KEY','ACCESS_TOKEN','REFRESH_TOKEN'))}
    env['SYX_STATE_DIR']=str(directory.resolve())
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(root),env=env)
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            for domain,path in [('trade','/settlement_pipeline/flows'),('services','/access_policy/cohort_rules'),('resources','/stockpile_bookkeeping/rows')]:
                page=await session.call_tool('query_game_state',{'domain':domain,'pointer':path})
                assert not page.is_error
                body=json.loads(next(c.text for c in page.content if c.type=='text'))
                assert body['coverage']=='unavailable' and body['data'] is None and body['total'] is None
                denied=await session.call_tool('select_game_state',{'spec':{'queries':[{'source':{'domain':domain,'path':path},'aggregates':{'n':{'op':'count'}}}]}})
                assert denied.is_error and 'observation is unavailable' in next(c.text for c in denied.content if c.type=='text')

def verify(directory:Path,timeout:float=260,on_demand:bool=False,tiles:bool=False,regional_live:bool=False):
    advisor=Advisor(directory/'snapshot.json',directory/'corpus.json')
    required={'city','settlement_battle','city_restored','battle_deployment','battle_menu','city_reloaded','world_generation','terrain_generated'}
    checks={};sessions={};began=time.monotonic();known_regional=None
    while time.monotonic()-began<timeout:
        try:
            phase=json.loads((directory/'phase.json').read_text());name=phase['phase']
            age=(datetime.now(timezone.utc)-datetime.fromisoformat(phase['started_at'].replace('Z','+00:00'))).total_seconds()
            if name not in required or name in checks or age<3:time.sleep(.25);continue
            snapshot=advisor.snapshot();status=advisor.status(snapshot);context=snapshot.ui_context;scene=snapshot.scene
            assert status['live'],status
            assert context.get('available'),context
            assert scene['active_view']==context['active_view']
            lists=context['world_list_panels']
            assert lists['coverage']=='unavailable' and all(lists[f] is None for f in ['army_list_present','player_realm_list_present','region_browser_present'])
            sessions[name]=snapshot.session_id
            if name in {'city','city_restored','city_reloaded'}:
                assert context['active_view']=='settlement'
                assert scene['settlement_exists'] and scene['settlement_scene_kind']=='city'
                assert snapshot.domains['population'].coverage=='partial'
                assert snapshot.domains['resources'].scope=='mixed_scene_logistics_and_player_trade_promises'
                assert snapshot.domains['resources'].data['field_definitions']['owned']['scope']=='mixed_scene_logistics_and_player_trade_promises'
                assert snapshot.domains['resources'].data['field_definitions']['stockpile_stored']['scope']=='instantiated_settlement_scene'
                assert snapshot.domains['trade'].scope=='mixed_city_trade_pipeline_and_campaign_ledger'
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
            services=snapshot.domains['services']
            if name not in {'world_generation','terrain_generated'}:
                assert services.coverage=='partial' and services.scope=='instantiated_settlement_scene'
                rooms=services.data['room_data']
                assert rooms['coverage']=='partial' and rooms['scope']=='instantiated_settlement_scene'
                assert rooms['failed_rooms']==0 and not rooms['truncated']
                assert len(rooms['rooms'])<=rooms['row_limit'] and rooms['scanned_rooms']<=rooms['scan_room_limit']
                policy=services.data['access_policy']
                assert policy['scope']=='instantiated_city_service_configuration'
                if scene['settlement_scene_kind']=='battlefield':
                    assert policy['coverage']=='unavailable' and policy['service_types']==[] and policy['cohort_rules']==[]
                else:
                    assert policy['coverage']=='partial' and policy['failed_service_types']==0 and not policy['truncated']
                    assert len(policy['cohort_rules'])==len(policy['service_types'])*policy['cohorts_per_service_type']<=policy['rule_row_limit']

            regional=snapshot.domains['world']
            if name not in {'world_generation','terrain_generated'}:
                assert regional.coverage=='partial'
                assert regional.scope=='game_or_world' # Established domain scope; field meanings narrow counts to campaign regions.
                data=regional.data
                assert not data['region_truncated'] and not data['population_truncated'] and data['population_failed_regions']==0
                assert data['region_count_total']==len(data['regions'])<=data['region_limit']
                ids={r['id'] for r in data['regions']}
                assert data['population_by_race'] and all(r['region_id'] in ids for r in data['population_by_race'])
                assert len(data['population_by_race'])<=data['population_row_limit']
            stockpiles=snapshot.domains['resources']
            if stockpiles.data is not None:
                books=stockpiles.data['stockpile_bookkeeping']
                assert books['scope']=='instantiated_city_stockpile_bookkeeping'
                if name in {'world_generation','terrain_generated'} or scene['settlement_scene_kind']=='battlefield':
                    assert books['coverage']=='unavailable' and books['rows'] is None
                else:
                    assert books['coverage']=='partial' and not books['truncated'] and books['failed_resources']==0
                    assert len(books['rows'])==books['scanned_resources']<=books['resource_limit']==1000
            city_trade=snapshot.domains['trade']
            if name not in {'world_generation','terrain_generated'}:
                assert city_trade.coverage=='partial' and city_trade.scope=='mixed_city_trade_pipeline_and_campaign_ledger'
                pipeline=city_trade.data['settlement_pipeline']
                assert pipeline['scope']=='instantiated_city_trade'
                if scene['settlement_scene_kind']=='battlefield':
                    assert pipeline['coverage']=='unavailable' and pipeline['policies']==[] and pipeline['flows']==[]
                    asyncio.run(unavailable_city_data_mcp(directory))
                else:
                    assert pipeline['coverage']=='partial' and pipeline['failed_resources']==0 and not pipeline['truncated']
                    assert len(pipeline['flows'])<=pipeline['flow_row_limit'] and len(pipeline['policies'])<=pipeline['resource_limit']
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
                selection={'tile_bounds':[0,0,1,1],'fields':['terrain','floor','room','minerals','path','ground_moisture'],
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
                    moisture=tile['data']['rows'][0]['ground_moisture']
                    assert moisture['available'] and set(moisture['data'])=={'base_fraction','stored_current_fraction'}
                    assert all(0<=v<=1 and abs(v*15-round(v*15))<1e-10 for v in moisture['data'].values())
                    assert tile['data']['next_cursor'] is None
                    tile_available=True
            if name not in {'world_generation','terrain_generated'}:
                output=regional.data['regional_output_bookkeeping']
                assert output['coverage']=='partial' and output['scope']=='campaign_world_regions'
                assert not output['truncated'] and output['failed_cells']==output['failed_resources']==0
                assert len(output['rows'])==output['scanned_cells']<=output['cell_limit']==10000
                assert len(output['schedules'])==output['scanned_resources']<=output['resource_limit']==1000
                assert output['scanned_regions']<=output['region_limit']==1023
            regional_available=None
            if regional_live:
                from syx_regions import query_regional_outputs
                if name not in {'world_generation','terrain_generated'}:
                    first=regional.data['regional_output_bookkeeping']['rows'][0]
                    known_regional=(first['region_id'],first['resource_id'])
                assert known_regional is not None
                spec={'region_ids':[known_regional[0]],'resource_ids':[known_regional[1]],
                    'fields':['accrued_output_raw'],'expected_session_id':snapshot.session_id}
                if name in {'world_generation','terrain_generated'}:
                    try:query_regional_outputs(advisor,spec)
                    except ValueError as error:assert 'No completed campaign world' in str(error),error
                    else:raise AssertionError('Generation must reject campaign regional reads')
                    regional_available=False
                else:
                    live=query_regional_outputs(advisor,spec)
                    assert live['scope']=='campaign_world_regions' and live['scene']['active_view']==context['active_view']
                    assert live['data']['rows'][0]['region_id']==known_regional[0]
                    assert live['data']['rows'][0]['resource_id']==known_regional[1]
                    regional_available=True
            checks[name]={'passed':True,'world_list_panel_coverage':lists['coverage'],'view':context['active_view'],'scene_kind':scene['settlement_scene_kind'],
                          'on_demand_read_available':read_available,'tile_read_available':tile_available,'ground_moisture_read_available':tile_available,'regional_live_read_available':regional_available,
                          'city_trade_pipeline_coverage':city_trade.data['settlement_pipeline']['coverage'] if city_trade.data else 'unavailable',
                          'world_population_coverage':regional.coverage,
                          'regional_output_coverage':regional.data['regional_output_bookkeeping']['coverage'] if regional.data else 'unavailable',
                          'service_room_coverage':services.data['room_data']['coverage'] if services.data else 'unavailable',
                          'service_policy_coverage':services.data['access_policy']['coverage'] if services.data else 'unavailable',
                          'production_coverage':production.coverage,
                          'production_room_coverage':production.data['room_data']['coverage'] if production.data else 'unavailable',
                          'stockpile_bookkeeping_coverage':stockpiles.data['stockpile_bookkeeping']['coverage'] if stockpiles.data else 'unavailable'}
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
    p.add_argument('--regional-live',action='store_true')
    args=p.parse_args();verify(args.state_dir,args.timeout,args.on_demand,args.tiles,args.regional_live)
