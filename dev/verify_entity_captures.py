"""Actual MCP capture/paging while the isolated game advances and changes population/view."""
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
    directory = directory.resolve()
    advisor = Advisor(directory/'snapshot.json',directory/'corpus.json')
    began = time.monotonic()
    while time.monotonic()-began < 180:
        try:
            expected = json.loads((directory/'entity-fixture.json').read_text())['expected']
            snapshot = advisor.snapshot()
            if advisor.status(snapshot)['live'] and snapshot.domains['entities'].data['total'] == expected['total']:
                break
        except (FileNotFoundError,json.JSONDecodeError,TypeError):
            pass
        await asyncio.sleep(.2)
    else:
        raise AssertionError('No matching isolated capture fixture')
    params = StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(Path(__file__).resolve().parent.parent),
                                   env={**os.environ,'SYX_STATE_DIR':str(directory)})
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            async def call(tool, args, error=None):
                result = await session.call_tool(tool,args)
                text = next(block.text for block in result.content if block.type == 'text')
                if error:
                    assert result.is_error and error.lower() in text.lower(),text
                    return text
                assert not result.is_error,text
                assert len(text.encode()) <= 65536,(tool,len(text.encode()))
                return json.loads(text)
            spec = {'fields':['id','tile_x','tile_y','stats','relationships'],'stat_ids':[expected['stat_id']],
                    'max_rows':2000,'scan_limit':100000,'expected_session_id':snapshot.session_id}
            created = await call('capture_live_entities',{'spec':spec})
            cap = created['capture']
            assert cap['row_count'] == expected['total'] == 1395 and 'rows' not in created
            token = cap['capture_id']
            await call('capture_live_entities',{'spec':{'fields':['id'],'max_rows':1}},error='row bound')
            await call('capture_live_entities',{'spec':{'fields':['id'],'scan_limit':1}},error='scan bound')
            first = await call('read_entity_capture',{'capture_id':token,'limit':20,'include_ui_context':True})
            assert first['captured_ui_context']['active_view'] == 'settlement'
            assert first['captured_ui_context']['selected_subject']['entity_id'] == expected['entity_id']
            print('PASS complete 1395-row capture, bounded metadata/page text, and row/scan failures',flush=True)
            (directory/'capture-mutate.request').write_text('fixture-only mutation\n')
            began = time.monotonic()
            while time.monotonic()-began < 30:
                try:
                    mutation = json.loads((directory/'capture-mutated.json').read_text())
                    current = advisor.snapshot()
                    if current.scene['active_view'] == 'world' and current.ui_context['known_overlays']['game_menu']:
                        break
                except (FileNotFoundError,json.JSONDecodeError,KeyError):
                    pass
                await asyncio.sleep(.2)
            else:
                raise AssertionError('After-update sampler did not export nonzero-speed menu/world context')
            paused=current
            await asyncio.sleep(2.2)
            refreshed=advisor.snapshot()
            assert refreshed.snapshot_id!=paused.snapshot_id and refreshed.ui_context['known_overlays']['game_menu']
            print('PASS after-update observer refreshes UI-paused nonzero-speed menu/world context',flush=True)
            (directory/'capture-resume.request').write_text('fixture-only resume\n')
            began=time.monotonic()
            while time.monotonic()-began<30:
                current=advisor.snapshot()
                if current.tick>cap['tick'] and current.scene['active_view']=='world' and not current.ui_context['known_overlays']['game_menu']:break
                await asyncio.sleep(.2)
            else:raise AssertionError('Fixture did not resume active simulation')
            again = await call('read_entity_capture',{'capture_id':token,'limit':20,'include_ui_context':True})
            assert again['rows'] == first['rows']
            assert again['capture']['tick'] == cap['tick']
            assert again['capture']['captured_at'] == cap['captured_at']
            assert again['captured_ui_context'] == first['captured_ui_context']
            assert again['current_state']['tick'] > cap['tick'] and again['current_state']['scene']['active_view'] == 'world'
            ids = []
            target = None
            offset = 0
            pages = 0
            while True:
                page = await call('read_entity_capture',{'capture_id':token,'offset':offset,'limit':20})
                assert page['capture']['tick'] == cap['tick'] and page['capture']['captured_at'] == cap['captured_at']
                for row in page['rows']:
                    ids.append(row['id'])
                    if row['id'] == expected['entity_id']:
                        target = row
                pages += 1
                if page['next_offset'] is None:
                    break
                offset = page['next_offset']
                assert pages < 101
            assert len(ids) == len(set(ids)) == expected['total']
            assert mutation['added_entity_id'] not in ids and target is not None
            assert target['stats'][0]['value'] == expected['stat_value']
            assert target['relationships']['workplace']['available']
            new = await call('capture_live_entities',{'spec':{'entity_ids':[mutation['added_entity_id']],
                             'fields':['id'],'max_rows':1}})
            new_page = await call('read_entity_capture',{'capture_id':new['capture']['capture_id']})
            assert new_page['rows'] == [{'id':mutation['added_entity_id']}]
            left,right = await asyncio.gather(*[call('read_entity_capture',{'capture_id':token,'limit':20}) for _ in range(2)])
            assert left['rows'] == right['rows'] == first['rows']
            print('PASS retained rows/context after active simulation, added citizen and world-view change; new capture sees addition',flush=True)
            report = {'passed':True,'game_version':snapshot.game_version,'captured_entities':len(ids),'pages':pages,
                      'original_capture_tick':cap['tick'],'later_game_tick':again['current_state']['tick'],
                      'all_pages_same_tick_and_time':True,'new_entity_excluded_from_old_capture':True,
                      'new_capture_sees_new_entity':True,'captured_ui_context_preserved':True,
                      'concurrent_mcp_pages':True,'row_and_scan_bounds_rejected':True,'mcp_text_cap_checked':True,'ui_paused_nonzero_speed_refresh':True,
                      'observer_phase':cap['observer_phase'],
                      'limits':['One bounded game update-thread observation, not a global worker-thread transaction.',
                                'Copied city with temporary fixture citizens; not a large-city performance benchmark.',
                                'This run does not exhaust lifecycle/battle/menu states; unit tests cover token expiry/eviction/session invalidation.']}
            (directory/'capture-validation.json').write_text(json.dumps(report,indent=2)+'\n')
            (directory/'verifier.done').write_text('passed\n')
            return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir',type=Path,required=True)
    args = parser.parse_args()
    asyncio.run(verify(args.state_dir))
