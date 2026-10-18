"""Check world population getters and a bounded cross-table query through actual MCP."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from syx_mcp import Advisor


async def verify(directory):
    root=Path(__file__).resolve().parent.parent;directory=directory.resolve()
    advisor=Advisor(directory/'snapshot.json',directory/'corpus.json');deadline=time.monotonic()+110
    while time.monotonic()<deadline:
        try:
            fixture=json.loads((directory/'world-fixture.json').read_text());snapshot=advisor.snapshot()
            if advisor.status(snapshot)['live'] and snapshot.domains['world'].coverage=='partial':break
        except (OSError,ValueError):pass
        await asyncio.sleep(.2)
    else:raise AssertionError('No live world fixture')
    env={k:v for k,v in os.environ.items() if not any(t in k for t in ('API_KEY','ACCESS_TOKEN','REFRESH_TOKEN'))}
    env['SYX_STATE_DIR']=str(directory)
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(root),env=env)
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            async def call(name,args):
                r=await session.call_tool(name,args);text=next(c.text for c in r.content if c.type=='text')
                assert not r.is_error,text
                assert len(text.encode())<=65536
                return json.loads(text)
            async def rows(path):
                found=[];offset=0
                while True:
                    r=await call('query_game_state',{'domain':'world','pointer':path,'offset':offset,'limit':100})
                    assert r['state']['session_id']==snapshot.session_id
                    found.extend(r['data']);offset=r['next_offset']
                    if offset is None:return found
            regions=await rows('/regions');population=await rows('/population_by_race')
            assert population==fixture['population']
            assert [{'id':r['id'],'total':r['population_total'],'capital':r['capital'],'area':r['area_world_tiles'],'player_owned':r['player_owned']} for r in regions]==fixture['regions']
            assert all(r['population_coverage']=='partial' for r in regions)
            data=snapshot.domains['world'].data
            assert not data['region_truncated'] and not data['population_truncated'] and not data['population_failed_regions']
            assert len(regions)==data['region_count_total']<=data['region_limit']==1023
            assert len(population)==len(regions)*fixture['race_count']<=data['population_row_limit']==10000
            assert fixture['race_count']<=data['race_scan_limit']==64
            indexed={r['id']:r for r in regions}
            assert any(r['player_owned'] for r in regions)
            query={'source':{'domain':'world','path':'/population_by_race'},
                'joins':[{'source':{'domain':'world','path':'/regions'},'left_key':'/region_id','right_key':'/id','as':'region','kind':'inner'}],
                'where':{'and':[{'gt':[{'field':'/population'},0]},{'eq':[{'field':'/region/player_owned'},True]}]},
                'select':{'region':{'field':'/region_id'},'race':{'field':'/race_id'},'inhabitants':{'field':'/population'},'area':{'field':'/region/area_world_tiles'}},
                'sort':[{'field':'/inhabitants','direction':'desc'}],'limit':5}
            selected=await call('select_game_state',{'spec':{'queries':[query],'include_ui_context':True}})
            expected=sorted([{'region':r['region_id'],'race':r['race_id'],'inhabitants':r['population'],'area':indexed[r['region_id']]['area_world_tiles']}
                for r in population if r['population']>0 and indexed[r['region_id']]['player_owned']],key=lambda r:r['inhabitants'],reverse=True)
            assert expected and selected['results'][0]['rows']==expected[:5]
            assert selected['results'][0]['matched_total']==len(expected)
            assert selected['ui_context']['available']
            fields=await call('describe_game_fields',{'domain':'world'})
            assert 'not the instantiated settlement' in fields['field_definitions']['population_total']['definition']
            report={'passed':True,'game_version':snapshot.game_version,'regions_checked':len(regions),'population_rows_checked':len(population),
                'playable_races_checked':fixture['race_count'],'public_getter_parity':True,'actual_mcp_paging_and_owned_region_join':True,
                'zero_population_rows_retained':any(r['population']==0 for r in population),'field_meanings_discoverable':True,'inference_calls':0,
                'limits':['Paused copied campaign only; no cap-exceeding mod, getter-failure injection, world growth forecast or huge-world performance test.',
                    'Regional stored counts and instantiated settlement citizens have distinct scopes; equal race keys establish identity only.',
                    'Only playable regional race counters from RDRaces.all are mapped; no complete hidden/non-playable population schema.']}
            (directory/'world-validation.json').write_text(json.dumps(report,indent=2)+'\n')
            (directory/'verifier.done').write_text('passed\n');print(json.dumps(report),flush=True)
            return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True)
    asyncio.run(verify(p.parse_args().state_dir))
