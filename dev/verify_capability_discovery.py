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
                assert result['game_version']=='0.71.44' and result['inventory_size']==358
                assert 'not an attestation' in result['warning']
                return result
            for identifier in ['room_workforce_factors','room_service_counters','service_cohort_permissions','city_trade_pipeline','regional_population_counters']:
                result=await call(identifier)
                assert len(result['capabilities'])==1
                record=result['capabilities'][0]
                assert record['id']==identifier and record['support']=='public_source_verified'
                assert record['validation'] and record['references'] and record['limits']
                assert 'documented stable contracts' in record['limits']
                checked.append({'id':identifier,'support':record['support'],'references':record['references'],'passed':True})
            for identifier in ['all_game_variables','all_states_and_menus']:
                result=await call(identifier)
                assert len(result['capabilities'])==1 and result['capabilities'][0]['support']=='unavailable'
                checked.append({'id':identifier,'support':'unavailable','passed':True})
            result=await call('RoomServiceInstance')
            assert {m['name'] for m in result['members']}=={'total','available','reserved'}
            for member in result['members']:
                assert member['public'] and len(member['source_candidates'])==1
                assert member['source_candidates'][0]['line']>0
                assert len(member['source_candidates'][0]['source_sha256'])==64
            report={'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),'checks':checked,
                'service_counter_member_anchors_checked':len(result['members']),'no_game_snapshot_required':not (directory/'snapshot.json').exists(),
                'inference_calls':0,'public_inventory_size':result['inventory_size'],
                'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in
                    ['syx_mcp.py','syx_api_support.py','syx_api_manifest.py','dev/verify_capability_discovery.py']},
                'limits':['Capability records summarize existing evidence; no new game getter/scene or official stable contract is established.',
                    'Offline discovery is not an attestation of a separately installed game mod; pair source-matching builds.',
                    'Five supported capabilities and two explicit gaps sampled, not exhaustive metadata acceptance.']}
            (directory/'capability-discovery-validation.json').write_text(json.dumps(report,indent=2)+'\n')
            print('Five data capabilities, two coverage gaps and three member anchors verified through MCP.')
            return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True)
    asyncio.run(verify(p.parse_args().state_dir))
