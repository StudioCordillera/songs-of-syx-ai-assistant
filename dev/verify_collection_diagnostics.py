"""Exercise collection diagnostics and query budgets through MCP using synthetic demo data.

No game process or inference. This validates response semantics, not game collector
cap/fault execution, real-scene availability or large-city performance.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def verify(directory):
    directory=directory.resolve();directory.mkdir(parents=True,exist_ok=False)
    snapshot=json.loads((ROOT/'snapshot.example.json').read_text())
    assert snapshot['demo'] is True
    snapshot['domains']['services']={'coverage':'partial','reason':'Synthetic limit/failure fixture','data':{
        'access_policy':{'coverage':'partial','scope':'synthetic_city_policy','truncated':True,
            'failed_service_types':2,'rule_row_limit':10000,
            'cohort_rules':[{'id':i,'allowed':False} for i in range(3)]}}}
    snapshot['domains']['resources']['data']={'rows':[{'id':i} for i in range(3)]}
    def write(): (directory/'snapshot.json').write_text(json.dumps(snapshot))
    write()
    env={k:v for k,v in os.environ.items() if not any(s in k for s in ('API_KEY','ACCESS_TOKEN','REFRESH_TOKEN'))}
    env['SYX_STATE_DIR']=str(directory)
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(ROOT),env=env)
    passed=[]
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            async def call(name,args,error=None):
                response=await session.call_tool(name,args)
                text=next(c.text for c in response.content if c.type=='text')
                if error:
                    assert response.is_error and error in text,text
                    return None
                assert not response.is_error,text
                result=json.loads(text)
                assert result['state']['demo'] and not result['state']['live']
                return result
            src={'domain':'services','path':'/access_policy/cohort_rules'}
            expected=[{'path':'/access_policy','truncated':True,'failed_service_types':2,'rule_row_limit':10000}]
            for offset in [0,2]:
                page=await call('query_game_state',{'domain':'services','pointer':src['path'],'offset':offset,'limit':2})
                assert page['collection_diagnostics']==expected and page['total']==3
                assert len(page['data'])==(2 if offset==0 else 1)
            passed.append('paged_reads_retain_collection_flags_across_pages')
            count=await call('select_game_state',{'spec':{'queries':[{'source':src,'aggregates':{'observed':{'op':'count'}}}]}})
            group=count['results'][0]
            assert group['rows']==[{'observed':3}] and group['sources'][0]['collection_diagnostics']==expected
            passed.append('aggregate_counts_exported_rows_with_explicit_truncation_and_failures')
            join={'source':{'domain':'resources','path':'/rows'},'joins':[{'source':src,'left_key':'/id','right_key':'/id','as':'policy'}]}
            result=await call('select_game_state',{'spec':{'queries':[join]}})
            assert len(result['results'][0]['rows'])==3 and result['results'][0]['sources'][1]['collection_diagnostics']==expected
            passed.append('joined_source_retains_own_collection_diagnostics')
            snapshot['domains']['services']['data']['access_policy']['coverage']='unavailable';write()
            await call('select_game_state',{'spec':{'queries':[{'source':src,'aggregates':{'n':{'op':'count'}}}]}},'observation is unavailable')
            passed.append('unavailable_source_refused_instead_of_counted_zero')
            snapshot['domains']['resources']['data']={'rows':[{'id':i} for i in range(10000)]};write()
            q={'source':{'domain':'resources','path':'/rows'},'aggregates':{'n':{'op':'count'}}}
            result=await call('select_game_state',{'spec':{'queries':[q]}})
            assert result['results'][0]['rows']==[{'n':10000}]
            snapshot['domains']['resources']['data']['rows'].append({'id':10000});write()
            await call('select_game_state',{'spec':{'queries':[q]}},'Source exceeds row budget')
            passed.append('source_budget_accepts_10000_refuses_10001')
            snapshot['domains']['resources']['data']={'rows':[{'id':0} for _ in range(101)]}
            snapshot['domains']['production']={'coverage':'partial','reason':'Synthetic','data':{'rows':[{'id':0} for _ in range(100)]}};write()
            join['joins'][0]['source']={'domain':'production','path':'/rows'};join['limit']=1
            await call('select_game_state',{'spec':{'queries':[join]}},'Join result exceeds row budget')
            passed.append('duplicate_join_row_cap_applies_before_limit')
            snapshot['domains']['resources']['data']={'rows':[{'id':i} for i in range(10000)]};write()
            q={'source':{'domain':'resources','path':'/rows'},'select':{'id':{'field':'/id'},'copy':{'field':'/id'}},'limit':1}
            await call('select_game_state',{'spec':{'queries':[q]*10}},'work budget exceeded')
            passed.append('batch_shares_work_budget')
    report={'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),'fixture':'synthetic demo only',
        'checks':passed,'inference_calls':0,'game_processes':0,
        'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in
            ['syx_query.py','syx_mcp.py','dev/verify_collection_diagnostics.py']},
        'limits':['Synthetic observations deliberately contain cap/failure flags; not runtime game collector cap or fault injection.',
            'No large-city, all-scene, live-game availability or provider advice acceptance.',
            'Collection diagnostics retain original ancestor paths and flag names; totals/aggregates cover exported rows only.',
            'Diagnostics do not scan descendants of projected containers; choose the table itself as a source/pointer.']}
    (directory/'collection-diagnostics-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Synthetic MCP collection diagnostics and query budget checks passed.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True)
    asyncio.run(verify(p.parse_args().state_dir))
