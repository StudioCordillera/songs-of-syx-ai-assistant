"""Native counter DTO parity plus actual MCP same-observation joins/aggregates and controls."""
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


async def verify(directory):
    root=Path(__file__).resolve().parent.parent;directory=directory.resolve()
    advisor=Advisor(directory/'snapshot.json',directory/'corpus.json');checks=[];deadline=time.monotonic()+150
    example=json.loads((root/'regional-output-query-example.json').read_text())
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(root),env={**os.environ,'SYX_STATE_DIR':str(directory)})
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            while len(checks)<4 and time.monotonic()<deadline:
                try:
                    fixture=json.loads((directory/'regional-output-fixture.json').read_text())
                    if fixture['step']!=len(checks):await asyncio.sleep(.2);continue
                    snapshot=advisor.snapshot()
                    if not advisor.status(snapshot)['live'] or snapshot.captured_at<datetime.fromisoformat(fixture['started_at'].replace('Z','+00:00')):
                        await asyncio.sleep(.2);continue
                    book=snapshot.domains['world'].data['regional_output_bookkeeping']
                    assert book['coverage']=='partial' and book['scope']=='campaign_world_regions'
                    assert not book['truncated'] and book['failed_cells']==book['failed_resources']==0
                    assert book['rows']==fixture['rows'] and book['schedules']==fixture['schedules']
                    assert len(book['rows'])==book['scanned_cells']<=book['cell_limit']==10000
                    assert len(book['schedules'])==book['scanned_resources']<=book['resource_limit']==1000
                    catalog={r.id:r for r in snapshot.references}
                    assert all(catalog[r['reference_id']].category=='resource' for r in book['schedules'])
                    regions={r['id']:r for r in snapshot.domains['world'].data['regions']}
                    schedules={r['resource_id']:r for r in fixture['schedules']}
                    positive=[r for r in fixture['rows'] if r['accrued_output_raw']>0]
                    ranked=sorted(positive,key=lambda r:-r['accrued_output_raw'])[:5]
                    expected=[{'region_id':r['region_id'],'region':regions[r['region_id']]['name'],
                        'faction_id':regions[r['region_id']]['faction_id'],'resource':r['resource_id'],
                        'accrued_output':r['accrued_output_raw'],'configured_days':schedules[r['resource_id']]['days_until_configured_output'],
                        'reference_id':r['reference_id']} for r in ranked]
                    described=await session.call_tool('describe_game_fields',{'domain':'world'})
                    assert not described.is_error,str(described)
                    meanings=json.loads(next(c.text for c in described.content if c.type=='text'))['field_definitions']['regional_output_bookkeeping']
                    assert meanings==book['field_definitions'] and meanings['accrued_output_raw']['unit']=='raw accrued resource items'
                    assert 'Not actual departure/arrival ETA' in meanings['days_until_configured_output']['definition']
                    spec={**example,'expected_snapshot_id':snapshot.snapshot_id}
                    spec['queries']=example['queries']+[{'source':{'domain':'world','path':'/regional_output_bookkeeping/rows'},
                        'aggregates':{'n':{'op':'count'},'total':{'op':'sum','value':{'field':'/accrued_output_raw'}}},'limit':1}]
                    response=await session.call_tool('select_game_state',{'spec':spec})
                    if response.is_error and 'Snapshot changed' in str(response):await asyncio.sleep(.2);continue
                    assert not response.is_error,str(response)
                    result=json.loads(next(c.text for c in response.content if c.type=='text'))
                    assert result['state']['snapshot_id']==snapshot.snapshot_id and result['ui_context']==snapshot.ui_context
                    assert result['results'][0]['rows']==expected and result['results'][0]['matched_total']==len(positive)
                    assert result['results'][1]['rows']==[{'n':len(fixture['rows']),'total':sum(r['accrued_output_raw'] for r in fixture['rows'])}]
                    diagnostics=result['results'][0]['sources'][0]['collection_diagnostics']
                    assert any(d['path']=='/regional_output_bookkeeping' and d['scanned_cells']==len(fixture['rows']) and d['failed_cells']==0 for d in diagnostics)
                    checks.append({'phase':fixture['phase'],'passed':True,'rows':len(fixture['rows']),
                        'schedules':len(fixture['schedules']),'positive_rows':len(positive),'all_native_cells_match':True,
                        'mcp_join_aggregate_context_parity':True})
                    if fixture['phase']=='restored':assert fixture['restored']
                    print('PASS',fixture['phase'],flush=True)
                    (directory/('regional-'+str(fixture['step'])+'.done')).write_text('verified\n')
                except (FileNotFoundError,json.JSONDecodeError):pass
                await asyncio.sleep(.2)
    if len(checks)!=4:raise AssertionError('Missing regional output export phases')
    report={'passed':True,'checks':checks,'controlled_counter_restored':True,'limits':[
        'One paused copied campaign, all loaded resource-backed outputs only. Public test controls hold one disposable value across observations and restore it; no saves.',
        'No owner-transfer/seasonal rollover, actual shipment/arrival, non-resource/MONEY output, cap/fault injection, all-mod or large-world performance acceptance.',
        'Stored accrual and cyclic configured offset are not inventory, delivered totals, production/income forecasts or departure/arrival ETA.']}
    (directory/'regional-output-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (directory/'verifier.done').write_text('complete\n');return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True)
    asyncio.run(verify(p.parse_args().state_dir))
