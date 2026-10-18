"""Actual live regional MCP pages, direct getter parity, authored cache truncation and scenes."""
import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sys
import time
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from syx_mcp import Advisor
from syx_regions import query_regional_outputs
from verify_scenes import verify as scenes


async def verify(directory):
    root=Path(__file__).resolve().parent.parent;directory=directory.resolve();advisor=Advisor(directory/'snapshot.json',directory/'corpus.json')
    start=time.monotonic()
    while time.monotonic()-start<100:
        try:
            fixture=json.loads((directory/'live-regional-fixture.json').read_text());s=advisor.snapshot()
            if advisor.status(s)['live'] and s.captured_at>=datetime.fromisoformat(fixture['started_at'].replace('Z','+00:00')):break
        except (FileNotFoundError,json.JSONDecodeError):pass
        await asyncio.sleep(.2)
    else:raise AssertionError('No fresh live regional fixture')
    fields=['accrued_output_raw','days_until_configured_output','reference_id','faction_id']
    base={'region_ids':fixture['region_ids'],'resource_ids':fixture['resource_ids'],'fields':fields,'limit':100}
    expected=fixture['rows'];target=[r for r in expected if r['region_id']==fixture['target_region'] and r['resource_id']==fixture['target_resource']][0]
    assert target['accrued_output_raw']==2147483647
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(root),env={**os.environ,'SYX_STATE_DIR':str(directory)})
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            async def call(spec):
                result=await session.call_tool('query_live_regional_outputs',{'spec':spec})
                assert not result.is_error,str(result)
                body=json.loads(next(c.text for c in result.content if c.type=='text'))
                assert body['session_id']==s.session_id and body['ui_context']['active_view']==body['scene']['active_view']
                return body
            pages=[];cursor=0;scanned=0
            while True:
                r=await call({**base,'cursor':cursor});pages.extend(r['data']['rows']);scanned+=r['data']['scanned_cells']
                assert r['data']['cell_errors']==0
                cursor=r['data']['next_cursor']
                if cursor is None:break
            assert pages==expected and scanned==len(expected)
            empty=await call({**base,'min_accrued_output':2147483647,'max_accrued_output':2147483647})
            assert empty['data']['rows']==[] and empty['data']['scanned_cells']==4096 and empty['data']['next_cursor']==4096
            final=await call({**base,'min_accrued_output':2147483647,'max_accrued_output':2147483647,'cursor':4096})
            assert final['data']['rows']==[target] and final['data']['next_cursor'] is None
            owned=next(r for r in expected if r['faction_id'] is not None)
            q={'region_ids':[owned['region_id']],'resource_ids':[owned['resource_id']],'fields':['faction_id'],
                'faction_id':owned['faction_id'],'min_accrued_output':owned['accrued_output_raw'],'max_accrued_output':owned['accrued_output_raw']}
            assert (await call(q))['data']['rows']==[{k:owned[k] for k in ['region_id','resource_id','faction_id']}]
            for spec,reason in [({'region_ids':[fixture['inactive_region']],'resource_ids':[fixture['target_resource']]},'inactive'),
                ({'region_ids':[fixture['target_region']],'resource_ids':['__unloaded_fixture_resource__']},'Unknown requested resource')]:
                failed=await session.call_tool('query_live_regional_outputs',{'spec':spec});assert failed.is_error and reason in str(failed)
            help_result=await session.call_tool('game_query_help',{});assert not help_result.is_error and 'on_demand_regional_outputs' in str(help_result)
    # A separate test MCP server deliberately exposes a truncated clone of the real
    # cached table, preserving actual session/time. The game and mailbox are unchanged.
    partial=StdioServerParameters(command=sys.executable,args=[str(root/'dev/regional_partial_cache_server.py')],cwd=str(root),
        env={**os.environ,'PYTHONPATH':str(root),'SYX_STATE_DIR':str(directory)})
    async with stdio_client(partial) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            page=await session.call_tool('query_game_state',{'domain':'world','pointer':'/regional_output_bookkeeping/rows','limit':1})
            cached=json.loads(next(c.text for c in page.content if c.type=='text'));assert cached['total']==100
            absent=await session.call_tool('select_game_state',{'spec':{'queries':[{
                'source':{'domain':'world','path':'/regional_output_bookkeeping/rows'},
                'where':{'and':[{'eq':[{'field':'/region_id'},fixture['target_region']]},
                    {'eq':[{'field':'/resource_id'},fixture['target_resource']]}]},
                'select':{'value':{'field':'/accrued_output_raw'}},'limit':1}]}})
            assert not absent.is_error,str(absent)
            cached_selection=json.loads(next(c.text for c in absent.content if c.type=='text'))['results'][0]
            assert cached_selection['rows']==[] and cached_selection['matched_total']==0
            assert any(d.get('cell_truncated') for d in cached_selection['sources'][0]['collection_diagnostics'])
            spec={'region_ids':[fixture['target_region']],'resource_ids':[fixture['target_resource']],'fields':fields}
            response=await session.call_tool('query_live_regional_outputs',{'spec':spec});assert not response.is_error,str(response)
            actual=json.loads(next(c.text for c in response.content if c.type=='text'));assert actual['data']['rows']==[target]
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs=[pool.submit(query_regional_outputs,advisor,{'region_ids':[r['region_id']],'resource_ids':[r['resource_id']],'fields':fields}) for r in [expected[0],expected[-1],expected[len(expected)//2]]]
        for job,expected_row in zip(jobs,[expected[0],expected[-1],expected[len(expected)//2]]):assert job.result()['data']['rows']==[expected_row]
    (directory/'live-regional.done').write_text('live queries verified\n')
    followup=await asyncio.to_thread(scenes,directory,260,True,True,True)
    restored=json.loads((directory/'live-regional-restored.json').read_text());assert restored['controlled_counter_restored']
    report={'passed':True,'native_rows_checked':len(expected),'matrix_pages':(len(expected)+99)//100,
        'empty_filtered_scan_cap_then_target':True,'controlled_counter_restored':True,'projection_and_combined_predicates':True,
        'unknown_inactive_id_refusal':True,'concurrent_requests_checked':3,'authored_partial_cache_rows':100,
        'live_mcp_target_missing_from_authored_cache':True,'scene_followup':followup,
        'limits':['Finite copied campaign and held/restored test-only counter; no normal saves or production writes.',
            'Partial-cache test clones/truncates the real DTO to 100 rows without refreshing timestamp/session or changing the live game. It is not an actual production 10000-cell cap fixture.',
            'Live pages are separate observations. No retained regional capture, global worker transaction, registry/cell fault injection, huge-world latency, income/inventory or actual delivery/arrival proof.']}
    (directory/'regional-live-validation.json').write_text(json.dumps(report,indent=2)+'\n');return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True)
    asyncio.run(verify(p.parse_args().state_dir))
