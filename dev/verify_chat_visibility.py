"""Verify own native render-callback limitations with current read-only MCP context."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import time
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client


async def verify(directory):
    directory=directory.resolve();root=Path(__file__).resolve().parent.parent
    env={k:v for k,v in {**os.environ,'SYX_STATE_DIR':str(directory)}.items() if not any(s in k.upper() for s in ['API_KEY','TOKEN'])}
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(root),env=env)
    checks={};required=['tooltip_empty_after_render','popup_and_reply_callbacks','hidden_active_without_callbacks'];deadline=time.monotonic()+95
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as mcp:
            await mcp.initialize()
            while time.monotonic()<deadline:
                if (directory/'chat-visibility-fixture-failure.json').exists():raise AssertionError('Native visibility probe failed')
                try:phase=json.loads((directory/'visibility-phase.json').read_text())
                except (FileNotFoundError,json.JSONDecodeError):await asyncio.sleep(.1);continue
                name=phase['phase']
                if name in checks:await asyncio.sleep(.1);continue
                assert name in required and phase['passed'] and phase['panel_activated']
                response=await mcp.call_tool('get_game_ui_context',{})
                if response.is_error:
                    await asyncio.sleep(.2);continue
                result=json.loads(next(c.text for c in response.content if c.type=='text'))
                context=result['context']
                if context.get('available') is not True:
                    await asyncio.sleep(.2);continue
                # Export may lag the newly held fixture phase; retry until the same public flag appears.
                if name=='popup_and_reply_callbacks' and not context['known_overlays']['popup']:
                    await asyncio.sleep(.2);continue
                if name=='hidden_active_without_callbacks' and not context['ui_hidden']:
                    await asyncio.sleep(.2);continue
                if name=='tooltip_empty_after_render':assert phase['paired_empty_public_box_callbacks']>=3 and phase['tooltip_draw_callbacks']>=3 and phase['reply_draw_callbacks']>=3
                elif name=='popup_and_reply_callbacks':assert phase['own_widget_bounds_overlap'] and phase['public_popup_showing'] and phase['reply_draw_callbacks']>=3 and phase['popup_draw_callbacks']>=3
                else:assert phase['stable_reply_callback_samples']>=5 and phase['updates_observed']>=5 and phase['ui_hidden']
                checks[name]=phase
                (directory/(name+'.done')).touch();print('PASS',name,flush=True)
                if len(checks)==3:break
    assert set(checks)==set(required),'Missing finite visibility phases'
    report=dict(passed=True,checks=checks,actual_mcp_known_popup_hidden_flags=True,
        production_badge_implemented=False,automatic_read_acknowledgements=0,external_inference_calls=0,
        limits=['Own public fixture widgets and native callbacks, not screenshot/pixel/physical-input or all-scene proof.',
            'Tooltip callback can precede an empty public GBox query; emptiness after rendering does not prove no tooltip was drawn.',
            'Overlapping popup and reply callbacks both execute; callback/activation alone does not establish unobscured display.',
            'Actual MCP verifies only existing known popup/hidden flags, not a tooltip/occlusion reader or a new production visibility field.',
            'Public GUI getter sampled by a test render callback is not approval for production game-state traversal from the rendering thread.',
            'No receipt broker/native renderer integration or general focus/occlusion contract is accepted by this negative probe.'])
    (directory/'chat-visibility-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (directory/'verifier.done').touch();print('Finite native visibility limitations verified',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True)
    asyncio.run(verify(p.parse_args().state_dir))
