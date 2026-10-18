"""Verify bounded current-recipe/recorded-flow observations through actual MCP."""
import argparse
import asyncio
import json
import hashlib
import math
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
        env={**{k:v for k,v in os.environ.items() if not any(t in k for t in ('API_KEY','ACCESS_TOKEN','REFRESH_TOKEN'))},'SYX_STATE_DIR':str(directory)})
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
            workforce_rows=await rows('employment','/rooms')
            employment={r['room_id']:r for r in workforce_rows}
            workforce_fixture=json.loads((directory/'workforce-fixture.json').read_text())
            expected_workforce=workforce_fixture['rooms']
            assert expected_workforce and len(workforce_rows)==len(expected_workforce)
            for actual,wanted in zip(workforce_rows,expected_workforce):
                assert {k:actual[k] for k in wanted}==wanted
            fetch_flags={r['work_factors']['fetch_factor_applies'] for r in workforce_rows}
            assert fetch_flags=={False,True},'Fixture must cover both conditional fetch branches'
            for room in workforce_rows:
                factors=room['work_factors'];assert type(factors['fetch_factor_applies']) is bool
                operands=[factors['efficiency_stored_raw'],factors['proximity_stored_raw']]
                if factors['fetch_factor_applies']:operands.append(factors['fetch_proximity_stored_raw'])
                calculated=math.prod(operands) if all(type(v) in (int,float) for v in operands) else None
                if calculated is None:assert factors['combined_efficiency_raw'] is None
                else:assert math.isclose(calculated,factors['combined_efficiency_raw'],rel_tol=1e-12,abs_tol=1e-12)
            workforce_meta=(await call('query_game_state',{'domain':'employment'}))['data']
            assert workforce_meta['coverage']=='partial' and not workforce_meta['truncated'] and workforce_meta['failed_rooms']==0
            assert workforce_meta['scanned_rooms']==workforce_fixture['scanned_rooms']<=10000
            assert workforce_meta['row_limit']==2000 and workforce_meta['scan_room_limit']==10000
            workforce_diagnostics=[{'path':'',**{k:workforce_meta[k] for k in
                ['scanned_rooms','failed_rooms','truncated','row_limit','scan_room_limit']}}]
            page=await call('query_game_state',{'domain':'employment','pointer':'/rooms','limit':1})
            assert page['collection_diagnostics']==workforce_diagnostics and page['total']==len(workforce_rows)
            factor_meanings=(await call('describe_game_fields',{'domain':'employment'}))['field_definitions']['work_factors']
            assert 'not worker counts' in factor_meanings['units'] and 'not instantaneous idle time' in factor_meanings['efficiency_stored_raw']
            assert 'Exact sample age' in factor_meanings['periods']
            factor_selection=await call('select_game_state',{'spec':json.loads((root/'workforce-query-example.json').read_text())})
            staffed=[r for r in workforce_rows if r['employed']>0]
            staffed.sort(key=lambda r:(r['work_factors']['combined_efficiency_raw'] is None,r['work_factors']['combined_efficiency_raw'] or 0))
            expected_staffed=[{'room':r['room_id'],'name':r['name'],'active':r['active'],'employed':r['employed'],'work_factors':r['work_factors']} for r in staffed[:5]]
            assert factor_selection['results'][0]['rows']==expected_staffed
            assert factor_selection['results'][0]['matched_total']==len(staffed)
            assert factor_selection['results'][0]['sources'][0]['collection_diagnostics']==workforce_diagnostics
            expected_outputs=[{'room':r['room_id'],'resource':r['resource_id'],'recorded_previous_day':r['previous_day_units'],
                'staffing':employment.get(r['room_id'])} for r in observed if r['direction']=='output']
            assert factor_selection['results'][1]['rows']==expected_outputs[:5]
            assert factor_selection['results'][1]['matched_total']==len(expected_outputs)
            assert factor_selection['results'][1]['sources'][1]['collection_diagnostics']==workforce_diagnostics
            assert factor_selection['ui_context']==snapshot.ui_context
            workforce_report={'passed':True,'game_version':snapshot.game_version,'employment_rooms_checked':len(workforce_rows),
                'scanned_rooms':workforce_meta['scanned_rooms'],'public_getter_parity':True,'conditional_combined_arithmetic':True,
                'fetch_factor_true_rooms':sum(r['work_factors']['fetch_factor_applies'] for r in workforce_rows),
                'fetch_factor_false_rooms':sum(not r['work_factors']['fetch_factor_applies'] for r in workforce_rows),
                'nondefault_factor_rooms':sum(any(v is not None and v!=1 for k,v in r['work_factors'].items() if k!='fetch_factor_applies') for r in workforce_rows),
                'first_page_and_selection_diagnostics':True,'stored_factors_and_recorded_output_join':True,
                'left_join_projects_staffing_object':True,'same_observation_ui_context':True,'field_meanings_discoverable':True,
                'inference_calls':0,'source_sha256':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in
                    ['mod/src/main/java/syx/assistant/StateCollector.java','mod/tests/ProductionScenario.java','dev/verify_production.py','workforce-query-example.json','syx_query.py','syx_mcp.py']},
                'limits':['Paused copied city with both countInput branches, not all room types or larger-city/cap/fault execution.',
                    'Raw stored/defaulted/smoothed factors; exact age unknown. No complete bonus stack, instantaneous productivity or throughput forecast.',
                    'Observer and fixture invoke no work/fetch/travel report, staffing setter, factor reset/update or save.']}
            (directory/'workforce-validation.json').write_text(json.dumps(workforce_report,indent=2)+'\n')
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
                'installed_reference_link':True,'workforce_factors':workforce_report,'stored_bucket_semantics_discoverable':True,
                'limits':['Paused copied city only. No forecast, complete recipe unlock schema, all room types or large-city performance established.',
                    '2000 flow-row/10000 room-scan caps are reported; a cap-exceeding city is not exercised by this fixture.',
                    'Stored buckets are not refreshed by observer and can retain older values; day accumulator includes fractional carry.']}
            (directory/'production-validation.json').write_text(json.dumps(report,indent=2)+'\n')
            (directory/'verifier.done').write_text('passed\n');print(json.dumps(report),flush=True)
            return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True)
    asyncio.run(verify(p.parse_args().state_dir))
