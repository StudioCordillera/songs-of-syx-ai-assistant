"""Actual per-warehouse MCP pages vs copied-city public getter rows, then scene refusals."""
import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from syx_mcp import Advisor
from syx_stockpiles import query_stockpiles
from verify_scenes import verify as scenes

ROOT=Path(__file__).resolve().parent.parent
FIELDS=['assigned_crates','stored_raw','capacity_raw','reserved_stored_raw','reserved_incoming_raw','reference_id']


async def verify(directory):
    start=time.monotonic();fixture_path=directory/'stockpile-live-fixture.json'
    while not fixture_path.is_file():
        if time.monotonic()-start>100:raise AssertionError('Timed out waiting for public getter fixture')
        await asyncio.sleep(.1)
    fixture=json.loads(fixture_path.read_text());expected=fixture['rows'];keys=fixture['resource_ids']
    assert expected and len(expected)<=10000
    advisor=Advisor(directory/'snapshot.json',directory/'corpus.json')
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(ROOT),env={**os.environ,'SYX_STATE_DIR':str(directory)})
    calls=0;bytes_max=0;requests=set();base={'resource_ids':keys,'fields':FIELDS,'scan_limit':5,'limit':3}
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize();listing=await session.list_tools()
            assert len(listing.tools)==19 and all(t.annotations.read_only_hint for t in listing.tools)
            async def call(spec):
                nonlocal calls,bytes_max
                result=await session.call_tool('query_live_stockpiles',{'spec':spec})
                assert not result.is_error,str(result)
                text=next(c.text for c in result.content if c.type=='text');body=json.loads(text);calls+=1
                assert body['request_id'] not in requests;requests.add(body['request_id'])
                bytes_max=max(bytes_max,len(text.encode()));assert bytes_max<=65536
                assert body['scope']=='instantiated_city_stockpile_bookkeeping' and body['observer_phase']=='GAME.addAfterUpdate'
                assert body['data']['cell_errors']==0
                assert body['scene']['active_view']==body['ui_context']['active_view']
                assert body['session_id']==advisor.snapshot().session_id
                return body
            rows=[];cursor=0;pages=0
            while True:
                r=await call({**base,'cursor':cursor});d=r['data'];rows+=d['rows'];pages+=1
                assert d['scanned_cells']==min(3,len(expected)-cursor)
                cursor=d['next_cursor']
                if cursor is None:break
            assert rows==expected
            cursor=0;empty_pages=0
            while True:
                d=(await call({**base,'cursor':cursor,'filters':[{'field':'stored_raw','op':'gt','value':2147483647}]}))['data']
                assert d['rows']==[] and d['scanned_cells']==min(5,len(expected)-cursor);empty_pages+=1
                cursor=d['next_cursor']
                if cursor is None:break
            first_room=fixture['room_ids'][0];room_rows=[r for r in expected if r['room_id']==first_room]
            explicit={'room_ids':[first_room],'resource_ids':keys,'fields':FIELDS,'limit':100}
            assert (await call(explicit))['data']['rows']==[{**r,'matrix_position':i} for i,r in enumerate(room_rows)]
            projected={**explicit,'fields':['stored_raw','reference_id']}
            drop=set(FIELDS)-set(projected['fields'])
            assert (await call(projected))['data']['rows']==[{k:v for k,v in {**r,'matrix_position':i}.items() if k not in drop} for i,r in enumerate(room_rows)]
            positive=[r for r in expected if r['stored_raw']>0 and r['capacity_raw']>0]
            assert positive and len(positive)<=100
            selected=await call({'resource_ids':keys,'fields':FIELDS,'limit':100,'filters':[
                {'field':'stored_raw','op':'gt','value':0},{'field':'capacity_raw','op':'gt','value':0}]})
            assert selected['data']['rows']==positive
            zero=[r for r in expected if r['capacity_raw']==0];assert zero and len(zero)<=100
            assert (await call({'resource_ids':keys,'fields':FIELDS,'limit':100,'filters':[{'field':'capacity_raw','op':'eq','value':0}]}))['data']['rows']==zero
            for room in [fixture['out_of_bounds_room'],fixture['non_warehouse_room']]:
                failed=await session.call_tool('query_live_stockpiles',{'spec':{**explicit,'room_ids':[room]}});assert failed.is_error,str(failed)
            failed=await session.call_tool('query_live_stockpiles',{'spec':{**explicit,'resource_ids':['__unloaded_warehouse_resource__']}})
            assert failed.is_error and 'Unknown requested resource key' in str(failed)
            help_result=await session.call_tool('game_query_help',{});assert not help_result.is_error and 'on_demand_stockpiles' in str(help_result)
            support=await session.call_tool('get_game_api_support',{'query':'live_warehouse_bookkeeping'});assert not support.is_error and 'public_source_verified' in str(support)
    # Three independent client objects use the same fixed shared transport lock.
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs=[pool.submit(query_stockpiles,Advisor(advisor.snapshot_path,advisor.corpus_path),
            {'room_ids':[r['room_id']],'resource_ids':[r['resource_id']],'fields':FIELDS,'limit':1}) for r in [expected[0],expected[-1],expected[len(expected)//2]]]
        for job,row in zip(jobs,[expected[0],expected[-1],expected[len(expected)//2]]):
            assert job.result()['data']['rows']==[{**row,'matrix_position':0}]
    (directory/'stockpile-live.done').write_text('warehouse queries verified\n')
    followup=await asyncio.to_thread(scenes,directory,260,True,True,True,True)
    assert len(followup['checks'])==8 and all(c['stockpile_live_read_available'] is not None for c in followup['checks'].values())
    sources=['mod/src/main/java/syx/assistant/StockpileReadRequest.java','mod/src/main/java/syx/assistant/AssistantScript.java',
        'mod/tests/StockpileLiveScenario.java','mod/tests/LiveSmoke.java','syx_stockpiles.py','dev/verify_live_stockpiles.py','dev/verify_scenes.py']
    report={'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),'native_rows_checked':len(expected),'matrix_pages':pages,
        'empty_filtered_pages':empty_pages,'successful_mcp_pages':calls,'maximum_tool_text_bytes':bytes_max,'concurrent_requests_checked':3,
        'getter_projection_zero_and_predicate_parity':True,'unknown_nonwarehouse_and_resource_refusal':True,
        'scene_followup':followup,'private_getter_fixture_sha256':hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
        'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sources},
        'limits':['One paused copied campaign warehouse matrix, not a large-city, real 4096-cell/100-row cap or injected registry/cell-fault case.',
            'Direct public resource-overload getters share stored arrays; not independent physical inventory or cross-page transaction truth.',
            'Eight actual scenes include generated battle deployment/menu, city reload and initial/terrain setup; no all-menu, natural battle conclusion or instant main-menu/unload coverage.',
            'No retained warehouse capture, durable room identity, selected warehouse, exact tally age, free goods, delivery or forecast claim.',
            'Production size/error guards have offline corruption/byte cases; observed native text fitting the budget is not a native byte-overflow fixture.',
            'All gameplay transitions are test-only public controls inside a validated copied profile/save. No provider calls or normal saves.']}
    (directory/'stockpile-live-validation.json').write_text(json.dumps(report,indent=2)+'\n');return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True)
    asyncio.run(verify(p.parse_args().state_dir))
