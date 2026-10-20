"""Production getter/DTO/retained-original MCP parity, then actual live weather scene guards."""
import argparse,asyncio,json,os,sys,time,shutil,hashlib
from datetime import datetime,timezone
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from verify_scenes import verify as scene_verify
ROOT=Path(__file__).resolve().parent.parent


async def verify(directory):
    checks=[]
    for phase in range(4):
        source=directory/f'weather-observation-{phase}.json';fixture=directory/f'weather-fixture-{phase}.json';start=time.monotonic()
        while not fixture.is_file():
            if time.monotonic()-start>100:raise AssertionError('Weather fixture timed out')
            await asyncio.sleep(.1)
        expected=json.loads(fixture.read_text());snapshot=json.loads(source.read_text());w=snapshot['domains']['map']['data']['weather']
        assert expected['getter_comparisons']==14 and w['coverage']=='partial' and w['data']==expected['expected_data']
        assert len(w['field_definitions'])==14 and w['tick']==snapshot['tick']==expected['tick']
        state=directory/f'weather-retained-{phase}';state.mkdir();shutil.copyfile(source,state/'snapshot.json')
        params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(ROOT),env={**os.environ,'SYX_STATE_DIR':str(state)})
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as mcp:
                await mcp.initialize()
                fields={k:{'field':'/factors/'+k} for k in w['data']['factors']};fields.update({k:{'field':'/flags/'+k} for k in w['data']['flags']})
                query={'queries':[{'source':{'domain':'map','path':'/weather/data'},'select':fields}],
                    'expected_snapshot_id':snapshot['snapshot_id'],'include_ui_context':True}
                r=await mcp.call_tool('select_game_state',{'spec':query});assert not r.is_error,str(r)
                result=json.loads(next(c.text for c in r.content if c.type=='text'))
                assert result['results'][0]['rows']==[{**w['data']['factors'],**w['data']['flags']}]
                assert result['state']['snapshot_id']==snapshot['snapshot_id'] and result['ui_context']==snapshot['ui_context']
                assert len(next(c.text for c in r.content if c.type=='text').encode())<=65536
                bad=await mcp.call_tool('select_game_state',{'spec':{**query,'expected_snapshot_id':'old-weather-observation'}})
                assert bad.is_error and 'Snapshot changed' in str(bad)
                definition=await mcp.call_tool('describe_game_fields',{'domain':'map'});assert not definition.is_error and 'temperature_scale' in str(definition)
                support=await mcp.call_tool('get_game_api_support',{'query':'stored_city_weather'});assert not support.is_error and 'public_source_verified' in str(support)
        if phase in [1,2]:assert w['data']['factors']['wind_strength']==phase-1
        if phase==3:assert snapshot['ui_context']['active_view']=='world'
        checks.append({'phase':phase,'same_game_update_getter_comparison':True,'same_snapshot_mcp_projection':True,'getter_values':14,'active_view':snapshot['ui_context']['active_view']})
        (directory/f'weather-{phase}.done').write_text('verified\n')
    scenes=await asyncio.to_thread(scene_verify,directory,260,True,True,True,True,True)
    assert len(scenes['checks'])==8 and all(c['weather_available'] is not None for c in scenes['checks'].values())
    names=['mod/src/main/java/syx/assistant/WeatherObservation.java','mod/src/main/java/syx/assistant/StateCollector.java',
        'mod/tests/WeatherScenario.java','mod/tests/SceneScenario.java','mod/tests/LiveSmoke.java','dev/verify_weather.py','dev/verify_scenes.py','dev/run_read_fixture.py']
    r={'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'scene_followup':scenes,'direct_getter_values':56,
        'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},'inference_calls':0,
        'limits':['Four actual production observations served as retained originals for precise same-callback getter/DTO/MCP parity; not substituted into the live mailbox.',
            'Eight subsequent actual live scene MCP checks validate city/tactical/reload availability and generated battle/setup refusal; no standalone menu/instant unload or all-state acceptance.',
            'Zero/one wind controls are public test-only mutations restored before scene handoff; no setter is used by the production observer.',
            'Native malformed stored doubles/getter exceptions, broad climates/seasons, crop productivity/forecasts and large-city/FPS cost remain unestablished.']}
    (directory/'weather-validation.json').write_text(json.dumps(r,indent=2)+'\n')
    return r


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True)
    asyncio.run(verify(p.parse_args().state_dir))
