"""Check actual MCP world-list membership/context with public-action copied-game phases."""
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

FIELDS=['army_list_present','player_realm_list_present','region_browser_present']


async def verify(directory):
    root=Path(__file__).resolve().parent.parent;directory=directory.resolve()
    advisor=Advisor(directory/'snapshot.json',directory/'corpus.json');checks=[]
    parameters=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(root),env={**os.environ,'SYX_STATE_DIR':str(directory)})
    async with stdio_client(parameters) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize();deadline=time.monotonic()+175
            while len(checks)<14 and time.monotonic()<deadline:
                try:
                    phase=json.loads((directory/'phase.json').read_text())
                    if phase['step']!=len(checks):await asyncio.sleep(.2);continue
                    source=advisor.snapshot()
                    if not advisor.status(source)['live']:await asyncio.sleep(.2);continue
                    response=await session.call_tool('get_game_ui_context',{})
                    assert not response.is_error,str(response)
                    observed=json.loads(next(c.text for c in response.content if c.type=='text'))
                    captured=datetime.fromisoformat(observed['state']['captured_at'].replace('Z','+00:00'))
                    if captured<datetime.fromisoformat(phase['started_at'].replace('Z','+00:00')):await asyncio.sleep(.2);continue
                    context=observed['context'];panels=context['world_list_panels']
                    assert context['known_overlays']['confirmation']==phase['modal']
                    assert context['ui_hidden']==phase['ui_hidden']
                    assert panels['coverage']==('partial' if phase['available'] else 'unavailable')
                    for field in FIELDS:
                        assert panels[field]==phase[field] and type(panels[field]) is (bool if phase['available'] else type(None))
                    assert 'selected_world_region' in context['unsupported'] and 'selected_world_army' in context['unsupported']
                    spec={'queries':[{'source':{'domain':'world','path':'/regions'},'limit':3,
                        'select':{'id':{'field':'/id'},**{field:{'context':'/world_list_panels/'+field} for field in FIELDS}}}],
                        'include_ui_context':True,'expected_snapshot_id':observed['state']['snapshot_id']}
                    selected=await session.call_tool('select_game_state',{'spec':spec})
                    if selected.is_error and 'Snapshot changed' in str(selected):await asyncio.sleep(.1);continue
                    assert not selected.is_error,str(selected)
                    result=json.loads(next(c.text for c in selected.content if c.type=='text'))
                    assert result['state']['snapshot_id']==observed['state']['snapshot_id']
                    assert result['ui_context']['world_list_panels']==panels
                    expected=[{'id':r['id'],**{f:phase[f] for f in FIELDS}} for r in source.domains['world'].data['regions'][:3]]
                    assert result['results'][0]['rows']==expected and expected
                    checks.append({'phase':phase['phase'],'passed':True,'coverage':panels['coverage'],
                        **{f:panels[f] for f in FIELDS},'ui_hidden':phase['ui_hidden'],'modal':phase['modal'],'same_observation_selection':True})
                    print('PASS',phase['phase'],flush=True)
                    (directory/('phase-'+str(phase['step'])+'.done')).write_text('verified\n')
                except (FileNotFoundError,json.JSONDecodeError):pass
                await asyncio.sleep(.2)
    if len(checks)!=14:raise AssertionError('Missing world-list context phases')
    report={'passed':True,'validated_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'inference_calls':0,
        'limits':['Fourteen phases in one paused copied campaign; public test-only panel/view/hide actions, no normal saves, native input or production mutations.',
            'True flags mean activated underlying manager membership, including behind confirmation or hidden UI. Inactive city/editor returns null. Known false in active completed world is distinct from unknown.',
            'Same-observation context projections do not identify selected regions/armies, list rows/search/sort, complete tab hierarchy or topmost visibility.',
            'No native getter-fault injection, every menu/mod/display or larger-city cost acceptance. Source-verified public readers are not documented stable contracts.']}
    (directory/'world-list-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (directory/'verifier.done').write_text('complete\n');return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True)
    asyncio.run(verify(p.parse_args().state_dir))
