"""Read-only verifier for ExtendedContextScenario's public UI/editor/retreat fixture."""
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
from assert_cached_viewport import validate_context
from syx_live import query_entities

async def transport(directory):
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(Path(__file__).resolve().parent.parent),
        env={**os.environ,'SYX_STATE_DIR':str(directory)})
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize();result=await session.call_tool('get_game_ui_context',{})
            assert not result.is_error,result
            response=json.loads(next(item.text for item in result.content if item.type=='text'))
            assert any(node.get('text')=='Primary popup label' for node in response['context']['known_content']['nodes'])

def verify(directory:Path,timeout=250):
    directory=directory.resolve();advisor=Advisor(directory/'snapshot.json',directory/'corpus.json')
    required={'city','popup','popup_secondary','section','content_budget','content_depth','content_closed',
        'text_input','full_screen_prompt','city_reloaded','world_editor','after_world_editor','battle_setup','after_battle_setup','battle_deployment','after_retreat'}
    checks={};sessions={};began=time.monotonic()
    while time.monotonic()-began<timeout:
        try:
            phase=json.loads((directory/'phase.json').read_text());name=phase['phase']
            age=(datetime.now(timezone.utc)-datetime.fromisoformat(phase['started_at'].replace('Z','+00:00'))).total_seconds()
            if name not in required or name in checks or age<3:time.sleep(.15);continue
            snapshot=advisor.snapshot();status=advisor.status(snapshot);context=snapshot.ui_context;scene=snapshot.scene
            assert status['live'] and context.get('available'),status
            content=context['known_content'];nodes=content['nodes'];flags=context['known_overlays']
            validate_context(context,scene)
            assert content['coverage']=='partial' and len(nodes)<=80
            assert sum(len(n.get('text','')) for n in nodes)<=4096
            assert all(len(n.get('text',''))<=512 for n in nodes)
            assert not context['overlay_order_known']
            sessions[name]=snapshot.session_id
            if name in {'popup','popup_secondary','section'}:
                root={'popup':'popup','popup_secondary':'popup_secondary','section':'section'}[name]
                label={'popup':'Primary popup label','popup_secondary':'Secondary popup label','section':'Section label'}[name]
                assert flags[root] and any(r['name']==root for r in content['roots'])
                assert any(n.get('text')==label for n in nodes)
                assert any(n.get('text')=='Nested readable label' for n in nodes)
                assert any(n.get('text')=='Readable switch label' for n in nodes)
                assert any(n.get('text')=='Hidden label' and not n['visible_through_known_ancestors'] for n in nodes)
                assert any(n.get('kind')=='control' and n.get('selected') and not n['active'] for n in nodes)
                assert any('refers_to_node_id' in n for n in nodes)
                assert 'Opaque button label' not in json.dumps(content)
                if name=='popup':asyncio.run(transport(directory))
            if name=='content_budget':assert content['truncated'] and len(nodes)==80 and any(n.get('text_truncated') for n in nodes)
            if name=='content_depth':assert content['truncated'] and 'Beyond depth budget' not in json.dumps(content)
            if name=='content_closed':assert not content['roots'] and not nodes and not flags['section']
            if name=='text_input':
                assert flags['text_input'] and 'Private input fixture value' not in json.dumps(context)
                assert not content['roots']
            if name=='full_screen_prompt':assert flags['full_screen_prompt'] and not flags['text_input']
            if name=='city_reloaded':assert snapshot.session_id!=sessions['city'] and context['active_view']=='settlement'
            if name=='world_editor':assert context['active_view']=='world_editor' and scene['world_generation']['is_editing']
            if name=='after_world_editor':
                assert context['active_view']=='settlement' and scene['world_generation']['is_editing']
                assert 'persist' in scene['world_generation']['flags_note']
            if name=='battle_setup':assert context['active_view']=='battle_setup' and scene['settlement_scene_kind']=='city'
            if name=='after_battle_setup':assert context['active_view']=='settlement'
            if name=='battle_deployment':
                assert context['active_view']=='battle' and scene['settlement_scene_kind']=='battlefield'
                assert context['battle_context']['deploying'] and 'does not prove active fighting' in context['battle_context']['phase_note']
            if name=='after_retreat':
                assert context['active_view']=='settlement' and scene['settlement_scene_kind']=='city'
                assert snapshot.session_id!=sessions['battle_deployment']
            if name in {'world_editor','battle_setup','after_retreat'}:
                read=query_entities(advisor,{'fields':['id'],'limit':1,'expected_session_id':snapshot.session_id})
                assert read['ui_context']['active_view']==context['active_view']
                assert read['scene']['settlement_scene_kind']==scene['settlement_scene_kind']
            checks[name]={'passed':True,'view':context['active_view'],'known_nodes':len(nodes),'truncated':content['truncated']}
            print('PASS',name,flush=True)
            if required<=checks.keys():break
        except (FileNotFoundError,json.JSONDecodeError):pass
        time.sleep(.15)
    missing=required-checks.keys()
    report={'passed':not missing,'checks':checks,'missing':sorted(missing),
        'limits':['Content tests use public game widgets built by the isolated fixture, not every native game dialog.',
            'Only three exposed roots and mapped widget types; no complete panel tree, final rendered visibility or global overlay order.',
            'Retreat is invoked from generated deployment. Active combat and victory/defeat UI are not validated.',
            'Editor activation is checked on a copied completed world, not every editing workflow or full new-world generation.']}
    (directory/'extended-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    if missing:raise AssertionError('Missing fixture phases: '+str(sorted(missing)))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True)
    verify(p.parse_args().state_dir)
