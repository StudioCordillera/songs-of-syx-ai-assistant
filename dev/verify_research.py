"""Check actual MCP research selections against copied-game public getter expectations.

Only metadata/counts are suitable for publication; fixture contents stay local.
"""
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
    directory=directory.resolve()
    advisor=Advisor(directory/'snapshot.json',directory/'corpus.json')
    deadline=time.monotonic()+100
    while time.monotonic()<deadline:
        try:
            fixture=json.loads((directory/'research-fixture.json').read_text())
            snapshot=advisor.snapshot()
            if advisor.status(snapshot)['live'] and snapshot.domains['research'].coverage=='partial':break
        except (FileNotFoundError,ValueError):pass
        await asyncio.sleep(.2)
    else:raise AssertionError('No fresh research fixture')
    root=Path(__file__).resolve().parent.parent
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(root),
        env={**os.environ,'SYX_STATE_DIR':str(directory)})
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            async def call(name,args):
                result=await session.call_tool(name,args)
                text=next(b.text for b in result.content if b.type=='text')
                assert not result.is_error,text
                assert len(text.encode())<=65536
                return json.loads(text)
            async def rows(path):
                result=[];offset=0
                while True:
                    response=await call('query_game_state',{'domain':'research','pointer':path,'offset':offset,'limit':100})
                    assert response['state']['session_id']==snapshot.session_id
                    result.extend(response['data'])
                    offset=response['next_offset']
                    if offset is None:return result
            actual={name:await rows('/'+name) for name in ('technologies','requirements','costs','currencies')}
            by_id={t['id']:t for t in actual['technologies']}
            assert fixture['technologies'] and fixture['requirements'] and fixture['costs'] and fixture['currencies']
            for name in actual:
                assert len(actual[name])==len(fixture[name])
                for observed,expected in zip(actual[name],fixture[name]):
                    assert all(observed[k]==v for k,v in expected.items()),(name,expected)
            for t in by_id.values():
                req=[r for r in actual['requirements'] if r['technology_id']==t['id']]
                assert t['technology_requirements_met']==all(r['current_level']>=r['required_level'] for r in req)
                assert t['reference_id']=='technology:'+t['id']
            for requirement in actual['requirements']:
                assert requirement['current_level']==by_id[requirement['required_technology_id']]['level']
                assert requirement['met']==(requirement['current_level']>=requirement['required_level'])
            for currency in actual['currencies']:
                assert currency['available']==currency['total']-currency['allocated']-currency['frozen']
            definitions=await call('describe_game_fields',{'domain':'research'})
            assert set(definitions['field_definitions'])=={'requirements','costs','currencies'}
            # Relational join/filter/projection: missing prerequisites with readable technology names.
            query={'source':{'domain':'research','path':'/requirements'},
                'joins':[{'source':{'domain':'research','path':'/technologies'},'left_key':'/required_technology_id',
                    'right_key':'/id','as':'required','kind':'inner'}],
                'where':{'eq':[{'field':'/met'},False]},
                'select':{'technology':{'field':'/technology_id'},'required':{'field':'/required/name'},
                    'missing_levels':{'subtract':[{'field':'/required_level'},{'field':'/current_level'}]}},'limit':3}
            selected=await call('select_game_state',{'spec':{'queries':[query],'include_ui_context':True}})
            expected_missing=[r for r in actual['requirements'] if not r['met']]
            assert selected['results'][0]['matched_total']==len(expected_missing)
            assert all(r['missing_levels']>0 for r in selected['results'][0]['rows'])
            assert len(selected['results'][0]['rows'])==min(3,len(expected_missing))
            assert 'ui_context' in selected
            # The dedicated selected person joins employment by a reviewed shared ID, in one observation.
            room_query={'source':{'domain':'entities','path':'/selected_subject'},
                'joins':[{'source':{'domain':'employment','path':'/rooms'},
                    'left_key':'/relationships/workplace/data/room_id','right_key':'/room_id','as':'work','kind':'inner'}],
                'select':{'entity_id':{'field':'/entity_id'},'room_id':{'field':'/work/room_id'},
                    'blueprint_id':{'field':'/work/blueprint_id'}},'limit':2}
            room_result=await call('select_game_state',{'spec':{'queries':[room_query],'include_ui_context':True}})
            assert room_result['results'][0]['rows']==[fixture['selection']]
            assert room_result['ui_context']['selected_subject']['entity_id']==fixture['selection']['entity_id']
            room_rows=[];offset=0
            while True:
                result=await call('query_game_state',{'domain':'employment','pointer':'/rooms','offset':offset,'limit':100})
                room_rows.extend(result['data']);offset=result['next_offset']
                if offset is None:break
            assert len(room_rows)==len(fixture['rooms'])
            assert len({r['room_id'] for r in room_rows})==len(room_rows)
            for row,expected in zip(room_rows,fixture['rooms']):
                assert row['room_id']==expected['room_id'] and row['blueprint_id']==expected['blueprint_id']
            # Mutate only the isolated fixture and wait for an observation containing the changed level.
            (directory/'research-cap.request').write_text('test only\n')
            while time.monotonic()<deadline:
                try:
                    capped=json.loads((directory/'research-cap.json').read_text())
                    latest=advisor.snapshot().domains['research'].data
                    t=next(t for t in latest['technologies'] if t['id']==capped['technology_id'])
                    if t['level']==capped['level']:break
                except (FileNotFoundError,ValueError):pass
                await asyncio.sleep(.2)
            else:raise AssertionError('No maximum-level observation')
            capquery={'source':{'domain':'research','path':'/costs'},
                'where':{'eq':[{'field':'/technology_id'},capped['technology_id']]},
                'select':{'next':{'field':'/next_level_cost'}},'limit':100}
            capped_result=await call('select_game_state',{'spec':{'queries':[capquery]}})
            assert capped_result['results'][0]['rows'] and all(r['next'] is None for r in capped_result['results'][0]['rows'])
            report={'passed':True,'game_version':snapshot.game_version,
                'rows_checked':{k:len(v) for k,v in actual.items()},
                'public_getter_parity':True,'prerequisite_level_invariants':True,'currency_balance_invariant':True,
                'mcp_relational_selection':True,'same_observation_ui_context':True,'max_level_cost_null':True,
                'field_meanings_discoverable':True,'employment_room_rows_checked':len(room_rows),
                'selected_worker_room_join':True,'room_id_unique_in_observation':True,
                'limits':['Paused copied city, then one test-only technology capped; original save is never written.',
                    'No full unlock decision, future production, all-menu or comprehensive game-variable coverage established.']}
            (directory/'research-validation.json').write_text(json.dumps(report,indent=2)+'\n')
            (directory/'verifier.done').write_text('passed\n')
            print(json.dumps(report),flush=True)
            return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir',type=Path,required=True)
    asyncio.run(verify(parser.parse_args().state_dir))
