"""Validate staged city-trade getters and bounded stock/policy joins through actual MCP."""
import argparse
import asyncio
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
            fixture=json.loads((directory/'trade-fixture.json').read_text());snapshot=advisor.snapshot();pipe=snapshot.domains['trade'].data['settlement_pipeline']
            if advisor.status(snapshot)['live'] and pipe['coverage']=='partial' and pipe['policies']==fixture['policies'] and pipe['flows']==fixture['flows']:break
        except (OSError,ValueError,KeyError,TypeError):pass
        await asyncio.sleep(.2)
    else:raise AssertionError('No matching live trade fixture')
    env={k:v for k,v in os.environ.items() if not any(t in k for t in ('API_KEY','ACCESS_TOKEN','REFRESH_TOKEN'))};env['SYX_STATE_DIR']=str(directory)
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(root),env=env)
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            async def call(name,args):
                r=await session.call_tool(name,args);text=next(c.text for c in r.content if c.type=='text');assert not r.is_error,text;assert len(text.encode())<=65536;return json.loads(text)
            async def rows(domain,path):
                result=[];offset=0
                while True:
                    r=await call('query_game_state',{'domain':domain,'pointer':path,'offset':offset,'limit':100});assert r['state']['session_id']==snapshot.session_id
                    result.extend(r['data']);offset=r['next_offset']
                    if offset is None:return result
            policies=await rows('trade','/settlement_pipeline/policies');flows=await rows('trade','/settlement_pipeline/flows')
            assert policies==fixture['policies'] and flows==fixture['flows']
            assert len(policies)==pipe['resource_count_total']<=pipe['resource_limit']==1000
            assert len(flows)==len(policies)*pipe['trade_type_count']<=pipe['flow_row_limit']==4000
            assert pipe['trade_type_count']<=pipe['trade_type_scan_limit']==16 and not pipe['truncated'] and pipe['failed_resources']==0
            assert snapshot.domains['trade'].scope=='mixed_city_trade_pipeline_and_campaign_ledger' and pipe['scope']=='instantiated_city_trade'
            assert all(r['inbound_total_units']==r['inbound_reserved_units']+r['inbound_pending_placement_units']+r['inbound_caravan_units'] for r in flows)
            assert all(r['outbound_total_units']==r['outbound_reserved_units']+r['outbound_caravan_units'] for r in flows)
            assert any(r['resource_id']==fixture['seeded_resource'] and r['trade_type_id']==fixture['trade_reason'] and r['inbound_reserved_units']>=4 and r['inbound_pending_placement_units']>=3 and r['outbound_reserved_units']>=5 for r in flows)
            assert any(r['resource_id']==fixture['seeded_resource'] and r['trade_type_id']==fixture['tax_reason'] and r['inbound_reserved_units']>=2 for r in flows)
            stocks={r['id']:r for r in await rows('resources','/stockpiles')};policy={r['resource_id']:r for r in policies}
            query={'source':{'domain':'trade','path':'/settlement_pipeline/flows'},'where':{'gt':[{'field':'/inbound_total_units'},0]},
                'joins':[{'source':{'domain':'resources','path':'/stockpiles'},'left_key':'/resource_id','right_key':'/id','as':'stock','kind':'inner'},
                         {'source':{'domain':'trade','path':'/settlement_pipeline/policies'},'left_key':'/resource_id','right_key':'/resource_id','as':'policy','kind':'inner'}],
                'select':{'resource':{'field':'/resource_id'},'reason':{'field':'/trade_type_id'},'inbound':{'field':'/inbound_total_units'},'stored':{'field':'/stock/stockpile_stored'},'buy_cap':{'field':'/policy/buy_price_cap_raw'}},'limit':5}
            selected=await call('select_game_state',{'spec':{'queries':[query],'include_ui_context':True}})
            eligible=[r for r in flows if r['inbound_total_units']>0 and r['resource_id'] in stocks and r['resource_id'] in policy]
            expected=[{'resource':r['resource_id'],'reason':r['trade_type_id'],'inbound':r['inbound_total_units'],'stored':stocks[r['resource_id']]['stockpile_stored'],'buy_cap':policy[r['resource_id']]['buy_price_cap_raw']} for r in eligible[:5]]
            assert selected['results'][0]['rows']==expected and selected['results'][0]['matched_total']==len(eligible) and selected['results'][0]['mixed_scopes']
            meanings=await call('describe_game_fields',{'domain':'trade'});assert 'not a current executable quote' in meanings['field_definitions']['trade_policy']['prices']
            report={'passed':True,'policies_checked':len(policies),'stage_rows_checked':len(flows),'trade_reasons_checked':pipe['trade_type_count'],
                'public_getter_parity':True,'public_stage_sum_parity':True,'controlled_nonzero_trade_tax_and_policy_cases':True,
                'actual_mcp_paging_stock_policy_join':True,'mixed_scope_and_field_meanings':True,'inference_calls':0,
                'limits':[fixture['fixture_note'],'Only resource tradables; no complete order list, world caravan positions, ETA, current executable quote or tariff-inclusive transaction test.',
                    'No nonzero caravan-counter scenario, cap-exceeding mods, getter-failure injection or large-city cost established.']}
            (directory/'trade-validation.json').write_text(json.dumps(report,indent=2)+'\n');(directory/'verifier.done').write_text('passed\n');print(json.dumps(report),flush=True)
            return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True);asyncio.run(verify(p.parse_args().state_dir))
