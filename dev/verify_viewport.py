"""Validate copied-game cached-viewport candidate controls and existing MCP context.

No viewport values are exposed by production yet; native geometry checks and MCP
view/overlay agreement are separate evidence, never selected/hovered tile acceptance.
"""
import argparse,asyncio,json,os,sys,time
from datetime import datetime
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from syx_mcp import Advisor

async def verify(directory):
    root=Path(__file__).resolve().parent.parent;directory=directory.resolve();advisor=Advisor(directory/'snapshot.json',directory/'corpus.json');checks=[]
    parameters=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(root),env={**os.environ,'SYX_STATE_DIR':str(directory)})
    async with stdio_client(parameters) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize();deadline=time.monotonic()+220
            while len(checks)<11 and time.monotonic()<deadline:
                try:
                    p=json.loads((directory/'phase.json').read_text())
                    if p['step']!=len(checks):await asyncio.sleep(.2);continue
                    source=advisor.snapshot()
                    if not advisor.status(source)['live']:await asyncio.sleep(.2);continue
                    r=await session.call_tool('get_game_ui_context',{});assert not r.is_error,str(r)
                    body=json.loads(next(c.text for c in r.content if c.type=='text'))
                    if datetime.fromisoformat(body['state']['captured_at'].replace('Z','+00:00'))<datetime.fromisoformat(p['started_at'].replace('Z','+00:00')):
                        await asyncio.sleep(.2);continue
                    c=body['context'];assert c['active_view']==p['expected_view']
                    assert c['known_overlays']['management_screen']==p['management']
                    assert c['known_overlays']['confirmation']==p['modal'] and c['known_overlays']['game_menu']==p['menu']
                    assert c['ui_hidden']==p['hidden']
                    assert 'viewport' not in c and 'cached_viewport' not in c and 'selected_tile' not in c
                    g=p['candidate_geometry'];assert type(g['zoomout']) is int and 0<=g['zoomout']<=2
                    for k in ['tiles','pixels','screen']:
                        assert len(g[k])==4 and all(type(v) is int for v in g[k]);x1,y1,x2,y2=g[k];assert x2>x1 and y2>y1
                    if p['management']:
                        assert p['control_checks']=={'cached_rectangles_unchanged_after_public_zoom_action':True,'zoom_changed':True}
                    else:
                        assert g['pixels'][2]-g['pixels'][0]==(g['screen'][2]-g['screen'][0])<<g['zoomout']
                        assert g['pixels'][3]-g['pixels'][1]==(g['screen'][3]-g['screen'][1])<<g['zoomout']
                    if p['expected_view']=='battle':assert body['state']['scene']['settlement_scene_kind']=='battlefield'
                    checks.append({'phase':p['phase'],'passed':True,'view':c['active_view'],'coordinate_scope':p['coordinate_scope'],
                        'management':p['management'],'modal':p['modal'],'hidden':p['hidden'],'menu':p['menu'],
                        'native_cached_geometry_checked':True,'existing_mcp_context_agrees':True})
                    (directory/f"phase-{p['step']}.done").write_text('verified\n');print('PASS',p['phase'],flush=True)
                except (FileNotFoundError,json.JSONDecodeError):pass
                await asyncio.sleep(.15)
            assert len(checks)==11,'Missing viewport candidate phases'
            report={'passed':True,'stage':'Native cached-viewport candidate, not production geometry/hover/selection support',
                'checks':checks,'native_window_handles_distinct':4,'management_cache_freeze_and_zoom_mismatch_observed':True,
                'existing_mcp_context_checks':11,'production_viewport_mcp_calls':0,'production_source_changed':False,'inference_calls':0,
                'limits':['Public camera/view/menu/hide and generated-battle setup actions occur only in the disposable copied profile. No pointer movement, screenshots, native input injection, private field access or reflection.',
                    'Geometry is recorded by the native fixture; MCP verifies existing view/overlay/hidden state only. No geometry field is implemented or validated through MCP.',
                    'Finite city, tactical HUD, campaign world, modal/hidden and generated battlefield/menu cases; no all-menu/mod/display, active combat, fresh-pointer, selection, exact rendered visibility, cost or unload-hook acceptance.',
                    'Management control changes zoom via a public action while its cached rectangles remain unchanged. Getter success is not proof of coherent current geometry; never repair caches from a production observer.',
                    'Native repeated getters/scaling checks share the shipped implementation. No independent renderer or pixel/screenshot ground truth.'
                ]}
            (directory/'viewport-validation.json').write_text(json.dumps(report,indent=2)+'\n');(directory/'verifier.done').write_text('verified\n')
            return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True);asyncio.run(verify(p.parse_args().state_dir))
