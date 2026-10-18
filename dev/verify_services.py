"""Compare public service counters and a staffing join through actual MCP."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from syx_mcp import Advisor


async def verify(directory):
    directory=directory.resolve();advisor=Advisor(directory/'snapshot.json',directory/'corpus.json')
    deadline=time.monotonic()+100
    while time.monotonic()<deadline:
        try:
            fixture=json.loads((directory/'service-fixture.json').read_text());snapshot=advisor.snapshot()
            if advisor.status(snapshot)['live'] and snapshot.domains['services'].coverage=='partial':break
        except (FileNotFoundError,ValueError):pass
        await asyncio.sleep(.2)
    else:raise AssertionError('No service fixture')
    env={k:v for k,v in os.environ.items() if not any(t in k for t in ('API_KEY','ACCESS_TOKEN','REFRESH_TOKEN'))}
    env['SYX_STATE_DIR']=str(directory)
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(ROOT),env=env)
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            async def call(name,args):
                reply=await session.call_tool(name,args)
                text=next(c.text for c in reply.content if c.type=='text')
                assert not reply.is_error,text
                assert len(text.encode())<=65536
                result=json.loads(text)
                if 'state' in result:assert result['state']['session_id']==snapshot.session_id
                return result
            expected_diagnostics={
                '/room_data':[{'path':'/room_data',**{k:snapshot.domains['services'].data['room_data'][k]
                    for k in ['scanned_rooms','failed_rooms','truncated','row_limit','scan_room_limit']}}],
                '/access_policy':[{'path':'/access_policy',**{k:snapshot.domains['services'].data['access_policy'][k]
                    for k in ['scanned_service_types','failed_service_types','truncated','service_type_limit',
                        'rule_row_limit','race_scan_limit','class_scan_limit','cohorts_per_service_type']}}]}
            async def rows(domain,path):
                values=[];offset=0
                while True:
                    result=await call('query_game_state',{'domain':domain,'pointer':path,'offset':offset,'limit':100})
                    if domain=='services':
                        parent='/'+path.split('/')[1]
                        assert result['collection_diagnostics']==expected_diagnostics[parent]
                    values.extend(result['data']);offset=result['next_offset']
                    if offset is None:return values
            observed=await rows('services','/room_data/rooms')
            assert observed==fixture['rooms'] and observed
            assert 'per-room stored service-point counters' in snapshot.domains['services'].reason
            assert len({r['room_id'] for r in observed})==len(observed)
            meta=(await call('query_game_state',{'domain':'services','pointer':'/room_data'}))['data']
            assert meta['coverage']=='partial' and meta['scope']=='instantiated_settlement_scene'
            assert meta['failed_rooms']==0 and not meta['truncated']
            assert meta['scanned_rooms']==fixture['scanned_rooms']<=meta['scan_room_limit']==10000
            assert len(observed)<=meta['row_limit']==2000
            employment={r['room_id']:r for r in await rows('employment','/rooms')}
            eligible=[r for r in observed if r['total_slots_raw']>0];assert eligible
            spec=json.loads((ROOT/'service-query-example.json').read_text())
            selected=await call('select_game_state',{'spec':spec})
            expected=[{'room':r['room_id'],'blueprint':r['blueprint_id'],'active':r['active'],
                'total_slots':r['total_slots_raw'],'available_slots':r['available_slots_raw'],
                'reserved_slots':r['reserved_slots_raw'],'staffing':employment.get(r['room_id'])} for r in eligible[:5]]
            assert selected['results'][0]['sources'][0]['collection_diagnostics']==expected_diagnostics['/room_data']
            assert selected['results'][0]['rows']==expected
            assert selected['results'][0]['matched_total']==len(eligible)
            assert selected['ui_context']==snapshot.ui_context
            definition=(await call('describe_game_fields',{'domain':'services'}))['field_definitions']['room_data']
            assert 'not daily throughput' in definition['total_slots_raw']
            assert 'need not equal reserved' in definition['reserved_slots_raw']
            for reference in {r['reference_id'] for r in observed}:
                response=await call('search_game_references',{'query':reference})
                assert any(r['id']==reference for r in response['results'])
            policy=snapshot.domains['services'].data['access_policy']
            assert policy['coverage']=='partial' and policy['scope']=='instantiated_city_service_configuration'
            assert not policy['truncated'] and policy['failed_service_types']==0
            types=await rows('services','/access_policy/service_types')
            rules=await rows('services','/access_policy/cohort_rules')
            assert types==fixture['service_types'] and rules==fixture['cohort_rules']
            assert len(types)==policy['scanned_service_types']<=policy['service_type_limit']==256
            assert len(rules)==len(types)*policy['cohorts_per_service_type']<=policy['rule_row_limit']==10000
            assert len({(r['service_id'],r['race_id'],r['class_id']) for r in rules})==len(rules)
            assert {r['allowed_by_configured_rule'] for r in rules}=={False,True}
            for cl,expected in [(fixture['seeded_denied_class'],False),(fixture['seeded_allowed_class'],True)]:
                seeded=next(r for r in rules if r['service_id']==fixture['seeded_service'] and r['race_id']==fixture['seeded_race'] and r['class_id']==cl)
                assert seeded['allowed_by_configured_rule'] is expected
            cohorts={(r['race_id'],r['class_id']):r['count'] for r in await rows('population','/by_race_class')}
            denied=[r for r in rules if not r['allowed_by_configured_rule'] and (r['race_id'],r['class_id']) in cohorts]
            chosen=await call('select_game_state',{'spec':json.loads((ROOT/'service-policy-query-example.json').read_text())})
            expected=[{'service':r['service_id'],'blueprint':r['blueprint_id'],'race':r['race_id'],'class':r['class_id'],
                'configured_allow':False,'scene_population':cohorts[r['race_id'],r['class_id']]} for r in denied[:5]]
            assert chosen['results'][0]['sources'][0]['collection_diagnostics']==expected_diagnostics['/access_policy']
            assert chosen['results'][0]['rows']==expected and chosen['results'][0]['matched_total']==len(denied)
            assert chosen['ui_context']==snapshot.ui_context
            meanings=(await call('describe_game_fields',{'domain':'services'}))['field_definitions']['access_policy']
            assert 'not effective individual eligibility' in meanings['allowed_by_configured_rule']
            assert 'Missing rules are not denial' in meanings['limits']
            for reference in {r['reference_id'] for r in types}:
                response=await call('search_game_references',{'query':reference})
                assert any(r['id']==reference for r in response['results'])
            report={'passed':True,'game_version':snapshot.game_version,'service_rooms_checked':len(observed),
                'scanned_rooms':fixture['scanned_rooms'],'service_types_checked':len(types),'cohort_rules_checked':len(rules),
                'configured_policy_getter_parity':True,'controlled_true_false_policy_cases':True,'policy_population_join':True,'public_getter_parity':True,'room_staffing_left_join':True,
                'same_observation_ui_context':True,'collection_diagnostics_on_every_service_page_and_selection':True,'installed_room_reference_links':True,
                'positive_counter_rows':{k:sum(r[k]>0 for r in observed) for k in ('total_slots_raw','available_slots_raw','reserved_slots_raw')},
                'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in
                    ('service-query-example.json','service-policy-query-example.json','dev/verify_services.py','mod/tests/ServiceScenario.java')},
                'limits':['Paused copied city only; no every-service-type or cap/failure injection coverage.',
                    'Raw reported service-point counters, not people/day, demand, individual access or guaranteed reachability.',
                    'Observer performs no refresh/report/load, reservation or permission writes. Test-only policy setters establish two cases in a copied city; no save writes.',
                    'Configured cohort rule is not effective eligibility: nobles/tourists and child-parent rules can differ. Registered services may have no built room.']}
            (directory/'service-validation.json').write_text(json.dumps(report,indent=2)+'\n')
            (directory/'verifier.done').write_text('passed\n');print(json.dumps(report),flush=True)
            return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True)
    args=p.parse_args()
    try:asyncio.run(verify(args.state_dir))
    finally:
        # Let the owned fixture exit cleanly even when an assertion fails.
        args.state_dir.joinpath('verifier.done').write_text('verifier finished\n')
