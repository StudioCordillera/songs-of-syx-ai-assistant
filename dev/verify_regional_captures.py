"""Actual regional MCP capture paging after copied counter/context changes and reload."""
import argparse
import asyncio
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sys
import time
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from syx_mcp import Advisor
from verify_scenes import verify as scenes
from verify_regional_cost import distribution


async def verify(directory):
    root=Path(__file__).resolve().parent.parent;directory=directory.resolve()
    advisor=Advisor(directory/'snapshot.json',directory/'corpus.json')
    began=time.monotonic()
    while time.monotonic()-began<120:
        try:
            fixture=json.loads((directory/'regional-capture-fixture.json').read_text());snapshot=advisor.snapshot()
            if advisor.status(snapshot)['live'] and snapshot.captured_at>=datetime.fromisoformat(fixture['started_at'].replace('Z','+00:00')):break
        except (FileNotFoundError,json.JSONDecodeError):pass
        await asyncio.sleep(.2)
    else:raise AssertionError('No fresh regional capture fixture')
    fields=['accrued_output_raw','days_until_configured_output','reference_id','faction_id']
    base={'region_ids':fixture['region_ids'],'resource_ids':fixture['resource_ids'],'fields':fields}
    expected=[r for r in fixture['rows'] if r['accrued_output_raw']>0]
    assert 100<len(expected)<=2000
    target=next(r for r in expected if r['region_id']==fixture['target_region'] and r['resource_id']==fixture['target_resource'])
    assert target['accrued_output_raw']==2147483647
    parameters=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(root),env={**os.environ,'SYX_STATE_DIR':str(directory)})
    async with stdio_client(parameters) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            listing=await session.list_tools();assert len(listing.tools)==19 and all(t.annotations.read_only_hint for t in listing.tools)
            async def call(name,args,error=None):
                result=await session.call_tool(name,args);text=next(c.text for c in result.content if c.type=='text')
                if error:
                    assert result.is_error and error.lower() in text.lower(),text
                    return text
                assert not result.is_error and len(text.encode())<=65536,text
                return json.loads(text)
            created=await call('capture_live_regional_outputs',{'spec':{**base,'min_accrued_output':1,'max_rows':len(expected)}})
            capture=created['capture'];token=capture['capture_id']
            assert capture['row_count']==len(expected) and capture['selection_complete'] and capture['scanned_cells']==len(fixture['rows'])==4200
            assert capture['cell_errors']==0 and 'rows' not in created and capture['capture_kind']=='regional_output'
            prefix=fixture['prefix_regions'];prefix_rows=fixture['rows'][:prefix*len(base['resource_ids'])]
            second=await call('capture_live_regional_outputs',{'spec':{**base,'region_ids':base['region_ids'][:prefix],'max_rows':len(prefix_rows)}})
            prefix_token=second['capture']['capture_id'];assert second['capture']['row_count']==len(prefix_rows)>100
            raw_response=json.loads((directory/'regional-response.json').read_text())
            assert raw_response['read_mode']=='regional_capture' and raw_response['data']['rows']==prefix_rows
            assert 65536<(directory/'regional-response.json').stat().st_size<=2*1024*1024
            await call('capture_live_regional_outputs',{'spec':{**base,'max_rows':2000}},error='max_rows')
            await call('capture_live_regional_outputs',{'spec':{**base,'scan_limit':4096}},error='matrix')
            for tool in ['read_entity_capture','read_tile_capture']:
                await call(tool,{'capture_id':token},error='missing')
            (directory/'regional-capture-change.request').write_text('Restore copied counter; change public view\n')
            began=time.monotonic()
            while time.monotonic()-began<30:
                try:
                    restored=json.loads((directory/'regional-capture-restored.json').read_text());current=advisor.snapshot()
                    if current.scene['active_view']=='world' and current.tick>capture['tick']:break
                except (FileNotFoundError,json.JSONDecodeError):pass
                await asyncio.sleep(.2)
            else:raise AssertionError('No later world context after copied counter restoration')
            fresh=await call('query_live_regional_outputs',{'spec':{'region_ids':[target['region_id']],'resource_ids':[target['resource_id']],
                'fields':['accrued_output_raw']}})
            assert fresh['data']['rows'][0]['accrued_output_raw']==fixture['original_value']!=2147483647
            empty=await call('capture_live_regional_outputs',{'spec':{**base,'min_accrued_output':2147483647,'max_rows':1}})
            assert empty['capture']['row_count']==0 and empty['capture']['scanned_cells']==4200
            assert (await call('read_regional_output_capture',{'capture_id':empty['capture']['capture_id']}))['rows']==[]
            before=(directory/'regional-request.txt').read_bytes()
            async def pages(cap,rows):
                result=[];offset=0;count=0
                while True:
                    page=await call('read_regional_output_capture',{'capture_id':cap['capture_id'],'offset':offset,'limit':100,'include_ui_context':True})
                    assert page['capture']['tick']==cap['tick'] and page['capture']['captured_at']==cap['captured_at']
                    assert page['capture']['request_id']==cap['request_id'] and page['captured_ui_context']['active_view']=='settlement'
                    assert page['current_state']['scene']['active_view']=='world'
                    result.extend(page['rows']);count+=1;offset=page['next_offset']
                    if offset is None:break
                assert result==rows
                return count
            filtered_pages=await pages(capture,expected);prefix_pages=await pages(second['capture'],prefix_rows)
            left,right=await asyncio.gather(*[call('read_regional_output_capture',{'capture_id':token,'limit':10}) for _ in range(2)])
            assert left['rows']==right['rows']==expected[:10]
            assert (directory/'regional-request.txt').read_bytes()==before,'Retained pages wrote a game request'
            help_body=await call('game_query_help',{});assert help_body['retained_regional_outputs']['create_tool']=='capture_live_regional_outputs'
            (directory/'regional-capture.done').write_text('Capture rows/context verified; counter already restored\n')
            followup=await asyncio.to_thread(scenes,directory,260,True,True,True)
            assert advisor.snapshot().session_id!=snapshot.session_id
            await call('read_regional_output_capture',{'capture_id':token},error='session/version')
            await call('read_regional_output_capture',{'capture_id':token},error='missing')
    summaries={}
    assert len(fixture['timings'])==64
    for name in ['filtered_matrix','near_row_bound']:
        samples=[s for s in fixture['timings'] if s['case']==name]
        assert [s['sample'] for s in samples]==list(range(32))
        summaries[name]={'first_sample':samples[0],
            'warm_collector_ms':distribution([s['collector_ns']/1e6 for s in samples[1:]]),
            'warm_encoding_utf8_ms':distribution([s['encoding_utf8_ns']/1e6 for s in samples[1:]]),
            'max_response_bytes':max(s['response_bytes'] for s in samples)}
    report={'passed':True,'filtered_rows':len(expected),'filtered_matrix_cells':4200,'filtered_pages':filtered_pages,
        'unfiltered_rows':len(prefix_rows),'unfiltered_pages':prefix_pages,'larger_than_live_response_64k':True,
        'exact_max_rows_complete':True,'row_overflow_and_scan_refusal':True,'empty_complete_selection':True,
        'counter_restored':True,'new_live_read_sees_restored_value':True,'original_capture_values_context_time_preserved':True,
        'no_game_request_while_paging':True,'concurrent_identical_pages':True,'cross_pool_token_refusal':True,
        'real_changed_session_token_invalidated':True,'scene_followup':followup,
        'native_samples':fixture['timings'],'native_cost_summary':summaries,
        'limits':['Finite copied paused campaign. Held max-int resource accrual restored before scene/battle/reload follow-up; no normal save writes.',
            '64 native collector/encoding samples with independent getter parity, 31 warm samples per shape. Not cold JVM/cache, largest-world/city, 10000-cell/2000-row worst-case cost or FPS acceptance.',
            'Scene follow-up covers existing finite live regional availability; new capture success sampled in city and retained paging in later world view, with refusal after real reload. Not capture creation in every menu/battle/generation state.',
            'No native registry/cell fault injection, 2 MiB native overflow or natural rollover/ownership change proof. Those overflow/fault/lifetime branches have distinct synthetic guards.',
            'A single callback does not freeze worker threads or establish a global game transaction. Stored accrual/schedule/owner meanings and exact-age limits remain unchanged.']}
    (directory/'regional-capture-validation.json').write_text(json.dumps(report,indent=2)+'\n');return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--state-dir',type=Path,required=True)
    asyncio.run(verify(parser.parse_args().state_dir))
