"""Actual MCP spatial selections checked against independent public-getter fixture expectations."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from syx_mcp import Advisor
from verify_scenes import verify as verify_scenes


async def verify(directory):
    directory=directory.resolve();advisor=Advisor(directory/'snapshot.json',directory/'corpus.json')
    started=time.monotonic()
    while time.monotonic()-started<180:
        try:
            fixture=json.loads((directory/'tile-fixture.json').read_text());snapshot=advisor.snapshot()
            if advisor.status(snapshot)['live'] and snapshot.scene['active_view']=='settlement':break
        except (FileNotFoundError,json.JSONDecodeError,TypeError):pass
        await asyncio.sleep(.2)
    else:raise AssertionError('No fresh isolated tile fixture')
    root=Path(__file__).resolve().parent.parent
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(root),
        env={**os.environ,'SYX_STATE_DIR':str(directory)})
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            async def call(spec,error=None):
                result=await session.call_tool('query_live_tiles',{'spec':spec})
                text=next(b.text for b in result.content if b.type=='text')
                if error:
                    assert result.is_error and error.lower() in text.lower(),text
                    return
                assert not result.is_error,text
                assert len(text.encode())<=65536
                result=json.loads(text);assert result['session_id']==snapshot.session_id
                assert result['observer_phase']=='GAME.addAfterUpdate'
                assert result['data']['predicate_errors']==0
                return result
            for expected in fixture['points']:
                x,y=expected['tile_x'],expected['tile_y']
                spec={'tile_bounds':[x,y,x+1,y+1],'fields':['terrain','floor','room','minerals','path'],'limit':1}
                result=await call(spec);row=result['data']['rows'][0]
                assert row['tile_x']==x and row['tile_y']==y
                assert all(row[f]['available'] for f in spec['fields']),row
                assert row['terrain']['data']['key']==expected['terrain']
                floor=row['floor']['data'];room=row['room']['data'];mineral=row['minerals']['data'];path=row['path']['data']
                assert (None if floor is None else floor['key'])==expected['floor']
                if floor is not None:assert floor['degradation_raw']==expected['degrade']
                assert (None if room is None else room['map_record_id'])==expected['room_record']
                if room is not None:
                    assert room['instance_room_id']==expected['instance_room']
                    assert room['blueprint_id']==expected['room_blueprint']
                assert (None if mineral is None else mineral['resource_id'])==expected['mineral']
                if mineral is not None:
                    assert mineral['amount_raw']==expected['amount_raw']
                    assert abs(mineral['amount_fraction']-expected['amount_raw']/63)<1e-12
                    reference=await session.call_tool('search_game_references',{'query':mineral['reference_id']})
                    assert not reference.is_error and mineral['reference_id'] in str(reference)
                assert path['availability']==expected['availability'] and path['throne_component_reachable']==expected['reachable']
                filters={'terrain_id':expected['terrain'],'has_room':room is not None,
                         'throne_component_reachable':expected['reachable']}
                if floor is not None:filters['floor_id']=expected['floor']
                if room is not None:filters['room_blueprint_id']=expected['room_blueprint']
                if mineral is not None:filters['mineral_resource_id']=expected['mineral']
                filtered=await call({**spec,**filters});assert len(filtered['data']['rows'])==1
            print('PASS tile field parity, absent/present floor/room/minerals, combined filters and installed references',flush=True)
            cursor=0;rows=[];pages=0
            while True:
                page=await call({'tile_bounds':fixture['rectangle'],'fields':['terrain','room'],
                    'terrain_id':fixture['terrain_filter'],'has_room':True,'cursor':cursor,'scan_limit':37,'limit':11})
                pages+=1;rows.extend([r['tile_x'],r['tile_y']] for r in page['data']['rows'])
                cursor=page['data']['next_cursor']
                if cursor is None:break
            assert rows==fixture['matching_coordinates'],(len(rows),len(fixture['matching_coordinates']))
            assert len({tuple(r) for r in rows})==len(rows)
            empty=await call({'tile_bounds':fixture['rectangle'],'terrain_id':'syx-fixture-unknown-terrain','scan_limit':1})
            assert empty['data']['rows']==[] and empty['data']['next_cursor']==1
            await call({'tile_bounds':[fixture['width'],0,fixture['width']+1,1]},error='Bounds exceed')
            await call({'tile_bounds':[0,0,1,1],'fields':['private']},error='literal')
            await call({'tile_bounds':[0,0,1,1],'expected_session_id':'different'},error='Session changed')
            print('PASS rectangular scan/paging and nonmatching/out-of-map/unsupported/session boundaries',flush=True)
            point=fixture['points'][0];x,y=point['tile_x'],point['tile_y']
            tile_result,entity_result=await asyncio.gather(
                session.call_tool('query_live_tiles',{'spec':{'tile_bounds':[x,y,x+1,y+1]}}),
                session.call_tool('query_live_entities',{'spec':{'fields':['id'],'limit':1}}))
            assert not tile_result.is_error and not entity_result.is_error
            report={'passed':True,'game_version':'0.71.44','point_cases':len(fixture['points']),
                'case_labels':[v['case'] for v in fixture['points']], 'pages':pages,'matching_tiles':len(rows),
                'field_parity':True,'null_presence_distinguished':True,'combined_filters':True,
                'mineral_installed_reference':True,'coordinate_and_cursor_bounds':True,'concurrent_tile_entity_requests':True,
                'mcp_text_cap_checked':True,'observer_phase':'GAME.addAfterUpdate',
                'limits':['Copied paused city; cursor pages remain separate mutable observations.',
                    'Scene follow-up covers city/tactical HUD/generated deployment/menu/reload/initial and terrain world setup; not active combat or every menu.',
                    'Room map record IDs can be shared; no UI-selected room, construction suitability, particular-agent route or yield forecast established.']}
            (directory/'tile-validation.json').write_text(json.dumps(report,indent=2)+'\n')
            (directory/'tile-verifier.done').write_text('passed\n')
    # The fixture advances into the existing public scene scenario after tile checks finish.
    return await asyncio.to_thread(verify_scenes,directory,220,True,True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--state-dir',type=Path,required=True)
    asyncio.run(verify(parser.parse_args().state_dir))
