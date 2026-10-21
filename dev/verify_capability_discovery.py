"""Check source-backed data capability discovery through actual offline MCP."""
import argparse
import asyncio
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client


async def verify(directory):
    directory=directory.resolve();directory.mkdir(parents=True,exist_ok=True)
    env={k:v for k,v in os.environ.items() if not any(s in k for s in ('API_KEY','ACCESS_TOKEN','REFRESH_TOKEN'))}
    env['SYX_STATE_DIR']=str(directory)
    parameters=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(ROOT),env=env)
    checked=[]
    async with stdio_client(parameters) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            async def call(query):
                response=await session.call_tool('get_game_api_support',{'query':query,'limit':30})
                text=next(c.text for c in response.content if c.type=='text')
                assert not response.is_error and len(text.encode())<=65536,text
                result=json.loads(text)
                assert result['game_version']=='0.71.44' and result['inventory_size']==len(json.loads((ROOT/'api-audit.json').read_text())['members'])
                assert 'not an attestation' in result['warning']
                return result
            for identifier in ['city_home_records','stored_city_weather','live_warehouse_bookkeeping','cached_viewport_geometry','tile_ground_moisture','world_list_panel_context','retained_regional_output_selections','live_regional_output_selections','regional_output_bookkeeping','retained_tile_selections','city_stockpile_bookkeeping','room_producer_degradation','entity_workplace_filter','room_workforce_factors','room_service_counters','service_cohort_permissions','city_trade_pipeline','regional_population_counters']:
                result=await call(identifier)
                assert len(result['capabilities'])==1
                record=result['capabilities'][0]
                assert record['id']==identifier and record['support']=='public_source_verified'
                assert record['validation'] and record['references'] and record['limits']
                assert any(s in record['limits'] for s in ['documented stable contracts','not stable documented contracts'])
                checked.append({'id':identifier,'support':record['support'],'references':record['references'],'passed':True})
            for identifier in ['all_game_variables','all_states_and_menus']:
                result=await call(identifier)
                assert len(result['capabilities'])==1 and result['capabilities'][0]['support']=='unavailable'
                checked.append({'id':identifier,'support':'unavailable','passed':True})
            home=await call('settlement.room.home.HOME')
            assert {m['name'] for m in home['members']}=={'occupant','occupants','occupantsMax','isolation','serviceX','serviceY'}
            assert all(m['public'] and len(m['source_candidates'])==1 for m in home['members'])
            result=await call('RoomServiceInstance')
            assert {m['name'] for m in result['members']}=={'total','available','reserved'}
            for member in result['members']:
                assert member['public'] and len(member['source_candidates'])==1
                assert member['source_candidates'][0]['line']>0
                assert len(member['source_candidates'][0]['source_sha256'])==64
            service_anchors=len(result['members'])
            factions=await call('UIFactions')
            assert {(m['name'],m['arity']) for m in factions['members']}=={('openIs',0),('openIs',1),('diploIs',1)}
            assert all(m['public'] and len(m['source_candidates'])==1 for m in factions['members'])
            world_ids=['view.world.WorldUI#armies','view.world.WorldUI#regions','view.world.WorldView#panels',
                'view.world.ui.army.UIArmies#listIsOpen(view.interrupter.ISidePanels)',
                'view.world.ui.region.UIRegions#allList','view.world.ui.region.UIRegions#playerList',
                'view.interrupter.ISidePanels#added(view.interrupter.ISidePanel)']
            for identifier in world_ids:
                anchors=await call(identifier)
                assert len(anchors['members'])==1 and anchors['members'][0]['id']==identifier
                member=anchors['members'][0]
                assert member['public'] and len(member['source_candidates'])==1 and member['source_candidates'][0]['line']>0
            stockpile_ids=['settlement.room.main.RoomsMap#getByIndex(int)','settlement.room.main.RoomsMap#max()',
                'settlement.room.infra.stockpile.StockpileTally.TallyData#get(int,settlement.room.infra.stockpile.StockpileInstance)',
                'snake2d.util.sets.LIST#get(int)']
            for identifier in stockpile_ids:
                anchors=await call(identifier)
                assert len(anchors['members'])==1 and anchors['members'][0]['id']==identifier
                member=anchors['members'][0]
                assert member['public'] and len(member['source_candidates'])==1 and member['source_candidates'][0]['line']>0
            weather_ids=['settlement.main.SETT#WEATHER()','settlement.weather.WeatherThing#getD()',
                'settlement.weather.WeatherGrowth#isAutumn()','settlement.weather.WeatherGrowthRipe#cropsAreRipe()',
                'settlement.weather.WeatherGrowthRipe#ripening()','settlement.weather.WeatherSnow#rainIsSnow()']
            for identifier in weather_ids:
                anchors=await call(identifier)
                assert len(anchors['members'])==1 and anchors['members'][0]['id']==identifier
                assert anchors['members'][0]['public'] and len(anchors['members'][0]['source_candidates'])==1
            viewport_ids=['view.sett.SettView#getWindow()','view.sett.invasion.SBattleView#getWindow()',
                'view.battle.BattleView#getWindow()','view.world.WorldView#window',
                'view.subview.GameWindow#tiles()','view.subview.GameWindow#pixels()',
                'view.subview.GameWindow#view()','view.subview.GameWindow#zoomout()']
            for identifier in viewport_ids:
                anchors=await call(identifier)
                assert len(anchors['members'])==1 and anchors['members'][0]['id']==identifier
                member=anchors['members'][0]
                assert member['public'] and len(member['source_candidates'])==1 and member['source_candidates'][0]['line']>0
            moisture_ids=['settlement.main.SETT#GROUND()','settlement.tilemap.ground.Ground#MOISTURE_BASE','settlement.tilemap.ground.Ground#MOISTURE_CURRENT']
            for identifier in moisture_ids:
                anchors=await call(identifier)
                assert len(anchors['members'])==1 and anchors['members'][0]['id']==identifier
                assert anchors['members'][0]['public'] and len(anchors['members'][0]['source_candidates'])==1
            report={'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),'checks':checked,
                'home_member_anchors_checked':len(home['members']),'weather_member_anchors_checked':len(weather_ids),'stockpile_member_anchors_checked':len(stockpile_ids),'viewport_member_anchors_checked':len(viewport_ids),'ground_moisture_member_anchors_checked':len(moisture_ids),'world_list_member_anchors_checked':len(world_ids),'service_counter_member_anchors_checked':service_anchors,'faction_context_member_anchors_checked':len(factions['members']),'no_game_snapshot_required':not (directory/'snapshot.json').exists(),
                'inference_calls':0,'public_inventory_size':result['inventory_size'],
                'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in
                    ['syx_mcp.py','syx_api_support.py','syx_api_manifest.py','dev/verify_capability_discovery.py']},
                'limits':['Capability records summarize existing evidence; no new game getter/scene or official stable contract is established.',
                    'Offline discovery is not an attestation of a separately installed game mod; pair source-matching builds.',
                    'Eighteen supported capabilities and two explicit gaps sampled, not exhaustive metadata acceptance.']}
            (directory/'capability-discovery-validation.json').write_text(json.dumps(report,indent=2)+'\n')
            print('Eighteen data capabilities, two coverage gaps and 40 selected public member anchors verified through MCP.')
            return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True)
    asyncio.run(verify(p.parse_args().state_dir))
