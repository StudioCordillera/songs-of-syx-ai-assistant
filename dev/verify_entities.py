"""Verify on-demand reads against EntityScenario's isolated public-API fixture."""
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
from syx_live import query_entities

def verify(directory:Path,timeout=200):
    directory=directory.resolve();advisor=Advisor(directory/'snapshot.json',directory/'corpus.json')
    began=time.monotonic();snapshot=None
    while time.monotonic()-began<timeout:
        try:
            fixture=json.loads((directory/'entity-fixture.json').read_text());expected=fixture['expected']
            snapshot=advisor.snapshot()
            if advisor.status(snapshot)['live'] and snapshot.domains['entities'].data['total']==expected['total']:break
        except (FileNotFoundError,json.JSONDecodeError,TypeError):pass
        time.sleep(.2)
    else:raise AssertionError('No matching live isolated fixture')
    assert snapshot is not None
    prefix=snapshot.domains['entities'].data
    assert prefix['truncated'] and expected['entity_id'] not in {x['id'] for x in prefix['items']}
    assert prefix['selected_subject']['entity_id']==expected['entity_id']
    reference=next(r for r in snapshot.references if r.id==f"stat:{expected['stat_id']}")
    assert reference.individual_getter_available and reference.stat_id==expected['stat_id']
    print('PASS target is beyond exported prefix and stat getter is discoverable',flush=True)
    pinned={'expected_session_id':snapshot.session_id}
    response=query_entities(advisor,{**pinned,'entity_ids':[expected['entity_id']],
        'fields':['id','race_id','class_id','humanoid_type_id','tile_x','tile_y','stats'],
        'stat_ids':[expected['stat_id']],'limit':1})
    row=response['data']['rows'][0]
    assert row['id']==expected['entity_id']
    for key in ['race_id','class_id','humanoid_type_id','tile_x','tile_y']:assert row[key]==expected[key]
    assert row['stats'][0]['value']==expected['stat_value'] and row['stats'][0]['reference_id']==f"stat:{expected['stat_id']}"
    assert response['ui_context']['selected_subject']['entity_id']==expected['entity_id']
    assert response['scene']['settlement_scene_kind']=='city'
    print('PASS direct identity, attributes, stat and same-response UI context',flush=True)
    filtered=query_entities(advisor,{**pinned,'cursor':expected['slot'],'scan_limit':1,'limit':1,
        'race_id':expected['race_id'],'class_id':expected['class_id'],'humanoid_type_id':expected['humanoid_type_id'],
        'tile_bounds':[expected['tile_x'],expected['tile_y'],expected['tile_x']+1,expected['tile_y']+1],
        'stat_filters':[{'stat_id':expected['stat_id'],'op':'eq','value':expected['stat_value']}],'fields':['id']})
    assert filtered['data']['rows']==[{'id':expected['entity_id']}] and filtered['data']['scanned_slots']==1
    rejected=query_entities(advisor,{**pinned,'entity_ids':[expected['entity_id']],
        'stat_filters':[{'stat_id':expected['stat_id'],'op':'ne','value':expected['stat_value']}],'fields':['id']})
    assert not rejected['data']['rows'] and rejected['data']['predicate_errors']==0
    print('PASS combined filters, scan cursor and rejecting predicate',flush=True)
    ids=[];cursor=0;pages=0
    while True:
        page=query_entities(advisor,{**pinned,'cursor':cursor,'fields':['id'],'limit':100})
        ids.extend(x['id'] for x in page['data']['rows']);pages+=1
        if page['data']['next_cursor'] is None:break
        assert page['data']['next_cursor']>cursor
        cursor=page['data']['next_cursor']
        assert pages<1000
    assert len(ids)==len(set(ids))==expected['total'] and expected['entity_id'] in ids
    print('PASS complete paused-scene traversal across',pages,'bounded pages',flush=True)
    try:query_entities(advisor,{**pinned,'fields':['stats'],'stat_ids':[100000],'limit':1})
    except ValueError as error:assert 'Unknown stat' in str(error)
    else:raise AssertionError('Unknown stat was accepted')
    async def mcp_check():
        params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(Path(__file__).resolve().parent.parent),
            env={**os.environ,'SYX_STATE_DIR':str(directory)})
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                async def read():
                    result=await session.call_tool('query_live_entities',{'spec':{**pinned,'entity_ids':[expected['entity_id']],'fields':['id'],'limit':1}})
                    assert not result.is_error,result
                    value=json.loads(next(x.text for x in result.content if x.type=='text'))
                    assert value['data']['rows']==[{'id':expected['entity_id']}]
                    return value['request_id']
                first,second=await asyncio.gather(read(),read());assert first!=second
    asyncio.run(mcp_check())
    print('PASS unknown-stat rejection and concurrent read-only MCP requests',flush=True)
    current=advisor.snapshot()
    assert current.domains['entities'].data['total']==expected['total']
    assert current.ui_context['selected_subject']['entity_id']==expected['entity_id']
    report={'passed':True,'game_version':snapshot.game_version,'live_entities':expected['total'],'prefix_limit':1000,
        'target_beyond_prefix':True,'pages':pages,'combined_filters':True,'concurrent_mcp_requests':True,
        'unknown_stat_rejected':True,'same_response_context':True,
        'limits':['Paused isolated copied game; not a performance benchmark.','Cursor pages are separate observations, not a stable multi-page snapshot.','No private attributes or arbitrary field/method invocation.']}
    (directory/'entity-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (directory/'verifier.done').write_text('passed\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True)
    verify(p.parse_args().state_dir)
