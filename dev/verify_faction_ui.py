"""Verify actual MCP same-observation faction context from a public-action copied fixture."""
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
    advisor=Advisor(directory/'snapshot.json',directory/'corpus.json');checked=[]
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(root),
        env={**os.environ,'SYX_STATE_DIR':str(directory)})
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize();deadline=time.monotonic()+175
            while len(checked)<11 and time.monotonic()<deadline:
                try:
                    phase=json.loads((directory/'phase.json').read_text())
                    if phase['step']!=len(checked):await asyncio.sleep(.2);continue
                    snapshot=advisor.snapshot()
                    if not advisor.status(snapshot)['live'] or snapshot.captured_at<datetime.fromisoformat(phase['started_at'].replace('Z','+00:00')):
                        await asyncio.sleep(.3);continue
                    # Let the MCP server's own snapshot cache advance to this phase.
                    response=await session.call_tool('get_game_ui_context',{})
                    if response.is_error:await asyncio.sleep(.3);continue
                    observed=json.loads(next(x.text for x in response.content if x.type=='text'))
                    if observed['state']['snapshot_id']!=snapshot.snapshot_id:await asyncio.sleep(.3);continue
                    context=observed['context'];panels=context['world_faction_panels']
                    assert context['known_overlays']['confirmation']==phase['modal']
                    if not phase['available']:
                        assert panels['coverage']=='unavailable' and panels['detail_faction'] is None and panels['list_open'] is None
                    else:
                        assert panels['coverage']=='partial' and panels['identity_search_complete']
                        assert panels['failed_factions']==0 and not panels['truncated']
                        assert 2<=panels['scanned_factions']<=panels['faction_limit']==1000
                        assert panels['list_open']==phase['list_open']
                        detail=panels['detail_faction']
                        assert detail==(None if phase['faction_id'] is None else
                            {'faction_id':phase['faction_id'],'diplomacy_tab':phase['diplomacy_tab']})
                        spec={'queries':[{'source':{'domain':'diplomacy','path':'/factions'},
                            'where':{'eq':[{'field':'/id'},{'context':'/world_faction_panels/detail_faction/faction_id'}]},
                            'select':{'id':{'field':'/id'},'name':{'field':'/name'},'stance':{'field':'/stance'}},'limit':5}],
                            'include_ui_context':True,'expected_snapshot_id':snapshot.snapshot_id}
                        selected=await session.call_tool('select_game_state',{'spec':spec})
                        if phase['faction_id'] is None:
                            assert selected.is_error and 'Field does not exist' in str(selected)
                            spec['queries'][0]['where']={'eq':[{'field':'/id'},None]}
                            selected=await session.call_tool('select_game_state',{'spec':spec})
                        assert not selected.is_error,str(selected)
                        result=json.loads(next(x.text for x in selected.content if x.type=='text'))
                        assert result['state']['snapshot_id']==snapshot.snapshot_id
                        assert result['ui_context']['world_faction_panels']==panels
                        expected=[r for r in snapshot.domains['diplomacy'].data['factions'] if r['id']==phase['faction_id']]
                        assert result['results'][0]['rows']==[{k:r[k] for k in ['id','name','stance']} for r in expected]
                        assert len(expected)==(0 if phase['faction_id'] is None else 1)
                    checked.append({'phase':phase['phase'],'passed':True,'available':phase['available'],
                        'detail_present':phase['faction_id'] is not None,'same_observation_select_checked':phase['available']})
                    print('PASS',phase['phase'],flush=True)
                    (directory/('phase-'+str(phase['step'])+'.done')).write_text('verified\n')
                except (FileNotFoundError,json.JSONDecodeError):pass
                await asyncio.sleep(.2)
    if len(checked)!=11:raise AssertionError('Missing faction UI phases')
    report={'passed':True,'validated_at':datetime.now(timezone.utc).isoformat(),'checks':checked,
        'limits':['Eleven phases in one paused copied city/world with two active NPC factions. Test-only panel/view actions are excluded from production.',
            'Presence/tab reads describe underlying panels and can remain true behind a modal; inactive-world contexts are unavailable.',
            'No complete tab tree, selected room/region, tooltip text, standalone menu hook, all-scene/faction cap/fault or large-city cost acceptance.']}
    (directory/'faction-ui-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (directory/'verifier.done').write_text('complete\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True)
    asyncio.run(verify(p.parse_args().state_dir))
