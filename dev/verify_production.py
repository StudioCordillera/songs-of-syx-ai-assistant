"""Verify bounded current-recipe/recorded-flow observations through actual MCP."""
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


async def verify(directory):
    directory=directory.resolve();advisor=Advisor(directory/'snapshot.json',directory/'corpus.json')
    deadline=time.monotonic()+100
    while time.monotonic()<deadline:
        try:
            fixture=json.loads((directory/'production-fixture.json').read_text());snapshot=advisor.snapshot()
            if advisor.status(snapshot)['live'] and snapshot.domains['production'].coverage=='partial':break
        except (FileNotFoundError,ValueError):pass
        await asyncio.sleep(.2)
    else:raise AssertionError('No production fixture')
    root=Path(__file__).resolve().parent.parent
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(root),
        env={**os.environ,'SYX_STATE_DIR':str(directory)})
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            async def call(name,args):
                reply=await session.call_tool(name,args)
                text=next(c.text for c in reply.content if c.type=='text')
                assert not reply.is_error,text
                assert len(text.encode())<=65536
                return json.loads(text)
            async def rows(domain,path):
                all_rows=[];offset=0
                while True:
                    reply=await call('query_game_state',{'domain':domain,'pointer':path,'offset':offset,'limit':100})
                    assert reply['state']['session_id']==snapshot.session_id
                    all_rows.extend(reply['data']);offset=reply['next_offset']
                    if offset is None:return all_rows
            observed=await rows('production','/room_data/flows')
            assert observed==fixture['flows']
            assert {r['direction'] for r in observed}=={'input','output'}
            meta=await call('query_game_state',{'domain':'production','pointer':'/room_data'})
            assert meta['data']['failed_rooms']==0 and not meta['data']['truncated']
            assert meta['data']['read_producer_rooms']==fixture['producer_rooms']
            assert meta['scope']=='mixed_scene_production_and_campaign_ledger'
            assert meta['data']['scope']=='instantiated_settlement_scene'
            assert len(observed)<=meta['data']['row_limit']==2000
            assert meta['data']['scanned_rooms']<=meta['data']['scan_room_limit']==10000
            employment={r['room_id']:r for r in await rows('employment','/rooms')}
            resources={r['id']:r for r in await rows('resources','/stockpiles')}
            assert all(r['resource_id'] in resources for r in observed)
            assert all(r['room_reference_id']=='room:'+r['blueprint_id'] for r in observed)
            eligible=[r for r in observed if r['direction']=='output' and r['room_id'] in employment]
            assert eligible
            query={'source':{'domain':'production','path':'/room_data/flows'},
                'where':{'eq':[{'field':'/direction'},'output']},
                'joins':[{'source':{'domain':'employment','path':'/rooms'},'left_key':'/room_id','right_key':'/room_id','as':'work','kind':'inner'},
                         {'source':{'domain':'resources','path':'/stockpiles'},'left_key':'/resource_id','right_key':'/id','as':'stock','kind':'inner'}],
                'select':{'room':{'field':'/room_id'},'resource':{'field':'/resource_id'},
                          'recorded_previous_day':{'field':'/previous_day_units'},'employed':{'field':'/work/employed'},
                          'stored':{'field':'/stock/stockpile_stored'}},'limit':5}
            selected=await call('select_game_state',{'spec':{'queries':[query],'include_ui_context':True}})
            assert selected['results'][0]['matched_total']==len(eligible)
            expected=[{'room':r['room_id'],'resource':r['resource_id'],'recorded_previous_day':r['previous_day_units'],
                       'employed':employment[r['room_id']]['employed'],'stored':resources[r['resource_id']]['stockpile_stored']} for r in eligible[:5]]
            assert selected['results'][0]['rows']==expected and selected['results'][0]['mixed_scopes']
            meanings=await call('describe_game_fields',{'domain':'production'})
            assert 'fractional carry' in meanings['field_definitions']['room_data']['periods']
            reference=await call('search_game_references',{'query':observed[0]['reference_id']})
            assert any(r['id']==observed[0]['reference_id'] for r in reference['results'])
            report={'passed':True,'game_version':snapshot.game_version,'flow_rows_checked':len(observed),
                'producer_rooms_checked':fixture['producer_rooms'],'public_getter_parity':True,
                'input_and_output_cases':True,'room_employment_resource_join':True,'mixed_scopes_reported':True,
                'installed_reference_link':True,'stored_bucket_semantics_discoverable':True,
                'limits':['Paused copied city only. No forecast, complete recipe unlock schema, all room types or large-city performance established.',
                    '2000 flow-row/10000 room-scan caps are reported; a cap-exceeding city is not exercised by this fixture.',
                    'Stored buckets are not refreshed by observer and can retain older values; day accumulator includes fractional carry.']}
            (directory/'production-validation.json').write_text(json.dumps(report,indent=2)+'\n')
            (directory/'verifier.done').write_text('passed\n');print(json.dumps(report),flush=True)
            return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True)
    asyncio.run(verify(p.parse_args().state_dir))
