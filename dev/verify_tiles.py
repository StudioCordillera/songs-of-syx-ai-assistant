"""Actual MCP spatial selections checked against independent public-getter fixture expectations."""
import argparse
import hashlib
import asyncio
import json
import os
from pathlib import Path
import sys
import time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from syx_mcp import Advisor
from verify_scenes import verify as verify_scenes
from dev.chat_target_transport import McpTargetDrafts
from dev.chat_target_queue import TargetQueue, TargetAdmission
from dev.chat_target_dispatch import TargetDispatch, model_question
from dev.chat_target_tasks import TargetTasks
from syx_chat_store import ChatStore
from uuid import uuid4


async def verify(directory,env_file=None):
    directory=directory.resolve();advisor=Advisor(directory/'snapshot.json',directory/'corpus.json')
    started=time.monotonic()
    while time.monotonic()-started<180:
        try:
            fixture=json.loads((directory/'tile-fixture.json').read_text());snapshot=advisor.snapshot()
            if advisor.status(snapshot)['live'] and snapshot.scene['active_view']=='settlement':break
        except (FileNotFoundError,json.JSONDecodeError,TypeError):pass
        await asyncio.sleep(.2)
    else:raise AssertionError('No fresh isolated tile fixture')
    root=Path(__file__).resolve().parent.parent
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(root),
        env={**os.environ,'SYX_STATE_DIR':str(directory)})
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            async def call(spec,error=None):
                result=await session.call_tool('query_live_tiles',{'spec':spec})
                text=next(b.text for b in result.content if b.type=='text')
                if error:
                    assert result.is_error and error.lower() in text.lower(),text
                    return
                assert not result.is_error,text
                assert len(text.encode())<=65536
                result=json.loads(text);assert result['session_id']==snapshot.session_id
                assert result['observer_phase']=='GAME.addAfterUpdate'
                assert result['data']['predicate_errors']==0
                return result
            for expected in fixture['points']:
                x,y=expected['tile_x'],expected['tile_y']
                spec={'tile_bounds':[x,y,x+1,y+1],'fields':['terrain','floor','room','minerals','path','ground_moisture'],'limit':1}
                result=await call(spec);row=result['data']['rows'][0]
                assert row['tile_x']==x and row['tile_y']==y
                assert all(row[f]['available'] for f in spec['fields']),row
                assert row['terrain']['data']['key']==expected['terrain']
                floor=row['floor']['data'];room=row['room']['data'];mineral=row['minerals']['data'];path=row['path']['data']
                moisture=row['ground_moisture']['data']
                assert moisture=={k:expected[k] for k in ['base_fraction','stored_current_fraction']}
                assert all(0<=v<=1 and abs(v*15-round(v*15))<1e-10 for v in moisture.values())
                assert (None if floor is None else floor['key'])==expected['floor']
                if floor is not None:assert floor['degradation_raw']==expected['degrade']
                assert (None if room is None else room['map_record_id'])==expected['room_record']
                if room is not None:
                    assert room['instance_room_id']==expected['instance_room']
                    assert room['blueprint_id']==expected['room_blueprint']
                assert (None if mineral is None else mineral['resource_id'])==expected['mineral']
                if mineral is not None:
                    assert mineral['amount_raw']==expected['amount_raw']
                    assert abs(mineral['amount_fraction']-expected['amount_raw']/63)<1e-12
                    reference=await session.call_tool('search_game_references',{'query':mineral['reference_id']})
                    assert not reference.is_error and mineral['reference_id'] in str(reference)
                assert path['availability']==expected['availability'] and path['throne_component_reachable']==expected['reachable']
                filters={'terrain_id':expected['terrain'],'has_room':room is not None,
                         'throne_component_reachable':expected['reachable']}
                if floor is not None:filters['floor_id']=expected['floor']
                if room is not None:filters['room_blueprint_id']=expected['room_blueprint']
                if mineral is not None:filters['mineral_resource_id']=expected['mineral']
                filtered=await call({**spec,**filters});assert len(filtered['data']['rows'])==1
            print('PASS tile field parity, absent/present floor/room/minerals, combined filters and installed references',flush=True)
            cursor=0;rows=[];pages=0
            while True:
                page=await call({'tile_bounds':fixture['rectangle'],'fields':['terrain','room'],
                    'terrain_id':fixture['terrain_filter'],'has_room':True,'cursor':cursor,'scan_limit':37,'limit':11})
                pages+=1;rows.extend([r['tile_x'],r['tile_y']] for r in page['data']['rows'])
                cursor=page['data']['next_cursor']
                if cursor is None:break
            assert rows==fixture['matching_coordinates'],(len(rows),len(fixture['matching_coordinates']))
            assert len({tuple(r) for r in rows})==len(rows)
            empty=await call({'tile_bounds':fixture['rectangle'],'terrain_id':'syx-fixture-unknown-terrain','scan_limit':1})
            assert empty['data']['rows']==[] and empty['data']['next_cursor']==1
            await call({'tile_bounds':[fixture['width'],0,fixture['width']+1,1]},error='Bounds exceed')
            await call({'tile_bounds':[0,0,1,1],'fields':['private']},error='literal')
            await call({'tile_bounds':[0,0,1,1],'expected_session_id':'different'},error='Session changed')
            print('PASS rectangular scan/paging and nonmatching/out-of-map/unsupported/session boundaries',flush=True)
            point=fixture['points'][0];x,y=point['tile_x'],point['tile_y']
            tile_result,entity_result=await asyncio.gather(
                session.call_tool('query_live_tiles',{'spec':{'tile_bounds':[x,y,x+1,y+1]}}),
                session.call_tool('query_live_entities',{'spec':{'fields':['id'],'limit':1}}))
            assert not tile_result.is_error and not entity_result.is_error
            async def tool(name,args,error=None):
                response=await session.call_tool(name,args)
                text=next(c.text for c in response.content if c.type=='text')
                if error:
                    assert response.is_error and error.lower() in text.lower(),text
                    return
                assert not response.is_error and len(text.encode())<=65536,text
                return json.loads(text)
            help_result=await tool('game_query_help',{})
            listed=await tool('query_game_state',{'domain':'map','pointer':'/tile_fields'})
            assert listed['data']==['terrain','floor','room','minerals','path','ground_moisture']
            assert help_result['on_demand_tiles']['selection']['properties']['fields']['items']['enum']==listed['data']
            assert help_result['retained_tiles']['create_tool']=='capture_live_tiles'
            spec={'tile_bounds':fixture['capture_rectangle'],'fields':['terrain','room'],'max_rows':100}
            made=await tool('capture_live_tiles',{'spec':spec});cap=made['capture'];token=cap['capture_id']
            retained_rows=[{k:v for k,v in row.items() if k!='ground_moisture'} for row in fixture['capture_rows']]
            moisture_rows=[{k:row[k] for k in ['tile_x','tile_y','ground_moisture']} for row in fixture['capture_rows']]
            await tool('capture_live_tiles',{'spec':{**spec,'fields':['terrain','room','ground_moisture']}},error='64 KiB')
            moisture=await tool('capture_live_tiles',{'spec':{**spec,'fields':['ground_moisture']}})
            assert moisture['capture']['row_count']==100 and moisture['capture']['selection_complete']
            moisture_token=moisture['capture']['capture_id']
            assert cap['row_count']==100 and cap['scanned_tiles']==100 and cap['selection_complete']
            assert cap['capture_kind']=='tile' and 'rows' not in made
            await tool('capture_live_tiles',{'spec':{'tile_bounds':[0,0,11,10],'fields':['terrain'],'max_rows':100}},error='Incomplete tile capture')
            empty_capture=await tool('capture_live_tiles',{'spec':{'tile_bounds':[0,0,64,64],
                'fields':['terrain'],'terrain_id':'syx-fixture-unknown-terrain'}})
            assert empty_capture['capture']['row_count']==0 and empty_capture['capture']['scanned_tiles']==4096
            empty_page=await tool('read_tile_capture',{'capture_id':empty_capture['capture']['capture_id']})
            assert empty_page['rows']==[] and empty_page['next_offset'] is None
            await tool('read_entity_capture',{'capture_id':token},error='missing')
            first=await tool('read_tile_capture',{'capture_id':token,'limit':11,'include_ui_context':True})
            assert first['rows']==retained_rows[:11]
            assert first['captured_ui_context']['active_view']=='settlement'
            target_wire=(directory/'tile-request.txt').read_bytes()
            target_adapter=McpTargetDrafts(session)
            target_history=ChatStore(directory/'target-queue-history')
            target_queue=TargetQueue(target_history);assert target_queue.initialize() is True
            target_chat=target_history.new(snapshot.session_id,model='deepseek-v4-pro')['chat_id']
            target_item=await target_adapter.stage(target_chat,'tile',token,limit=2)
            target_initial=await target_adapter.prepare(target_chat)
            assert target_initial['attachments'][0]['rows']==retained_rows[:2]
            assert target_item['capture']['request_id']==cap['request_id']
            assert target_item['capture']['tick']==cap['tick']
            assert (directory/'tile-request.txt').read_bytes()==target_wire
            target_request=dict(chat_id=target_chat,request_id=str(uuid4()),turn_id=str(uuid4()),game_session=snapshot.session_id,
                text='Explain the two selected retained tile observations',attachment_ids=[target_item['attachment_id']])
            target_admission=TargetAdmission(target_queue,target_adapter)
            accepted=await target_admission.accept(**target_request)
            accepted_evidence=target_queue.accepted_evidence(target_request['request_id'])
            assert accepted_evidence['attachments'][0]['rows']==retained_rows[:2]
            assert target_history.turns(target_chat)[0]['status']=='queued'
            assert [e['kind'] for e in target_history.events(target_chat)]==['user','target_evidence']
            await target_admission.acknowledge(target_request)
            assert target_adapter.preview(target_chat)==[]
            target_item=await target_adapter.stage(target_chat,'tile',token,limit=2)
            target_history.close()
            target_history=ChatStore(directory/'target-queue-history',recover=True)
            target_queue=TargetQueue(target_history);assert target_queue.initialize() is False
            target_admission=TargetAdmission(target_queue,target_adapter)
            assert await target_admission.accept(**target_request)==accepted
            await target_admission.acknowledge(target_request)
            assert target_adapter.preview(target_chat)==[target_item]
            assert target_history.turns(target_chat)[0]['status']=='queued'
            assert target_queue.accepted_evidence(target_request['request_id'])==accepted_evidence
            target_history.close()
            assert (directory/'tile-request.txt').read_bytes()==target_wire
            (directory/'tile-capture-advance.request').write_text('test-only public view/speed change\n')
            began=time.monotonic()
            while time.monotonic()-began<30:
                current=advisor.snapshot()
                if current.tick>cap['tick'] and current.scene['active_view']=='world':break
                await asyncio.sleep(.2)
            else:raise AssertionError('Copied tile scene did not advance/change view')
            try:await target_adapter.prepare(target_chat)
            except ValueError as error:assert 'scene changed' in str(error),str(error)
            else:raise AssertionError('Target preparation accepted changed native scene')
            assert target_adapter.preview(target_chat)==[target_item]
            wire=(directory/'tile-request.txt').read_bytes();captured=[];offset=0;retained_pages=0
            while True:
                page=await tool('read_tile_capture',{'capture_id':token,'offset':offset,'limit':11,'include_ui_context':True})
                assert page['capture']['tick']==cap['tick'] and page['capture']['captured_at']==cap['captured_at']
                assert page['capture']['request_id']==cap['request_id'] and page['captured_ui_context']==first['captured_ui_context']
                assert page['current_state']['scene']['active_view']=='world'
                captured.extend(page['rows']);retained_pages+=1;offset=page['next_offset']
                if offset is None:break
            assert captured==retained_rows
            left,right=await asyncio.gather(*[tool('read_tile_capture',{'capture_id':token,'limit':11}) for _ in range(2)])
            assert left['rows']==right['rows']==first['rows']
            moisture_pages=[await tool('read_tile_capture',{'capture_id':moisture_token,'offset':i,'limit':10,'include_ui_context':True}) for i in range(0,100,10)]
            assert [r for page in moisture_pages for r in page['rows']]==moisture_rows
            assert all(page['capture']['request_id']==moisture['capture']['request_id'] and page['capture']['tick']==moisture['capture']['tick'] and page['capture']['captured_at']==moisture['capture']['captured_at'] for page in moisture_pages)
            assert all(page['captured_ui_context']['active_view']=='settlement' and page['current_state']['scene']['active_view']=='world' for page in moisture_pages)
            assert (directory/'tile-request.txt').read_bytes()==wire
            (directory/'tile-capture-city.request').write_text('test-only public city/pause restore\n')
            began=time.monotonic()
            while time.monotonic()-began<20:
                if advisor.snapshot().scene['active_view']=='settlement':break
                await asyncio.sleep(.2)
            else:raise AssertionError('Copied tile city was not restored')
            assert (await target_adapter.prepare(target_chat))['attachments'][0]['rows']==retained_rows[:2]
            fresh=await tool('capture_live_tiles',{'spec':{'tile_bounds':[x,y,x+1,y+1],'fields':['ground_moisture']}})
            try:await target_adapter.prepare(target_chat)
            except ValueError as error:assert 'unavailable' in str(error),str(error)
            else:raise AssertionError('Target preparation accepted evicted native token')
            assert target_adapter.preview(target_chat)==[target_item]
            await target_adapter.remove(target_chat,target_item['attachment_id'])
            replacement=await target_adapter.stage(target_chat,'tile',fresh['capture']['capture_id'])
            assert (await target_adapter.prepare(target_chat))['attachments']==[replacement]
            # Explicit developer dispatch AFTER original pool eviction: original accepted
            # rows are historical evidence, not live retained-token authority.
            target_history=ChatStore(directory/'target-queue-history',recover=True)
            target_queue=TargetQueue(target_history)
            class FixtureProvider:
                calls=0
                closed=False
                async def complete(self,messages,tools,on_text):
                    self.calls+=1
                    question=next(m['content'] for m in messages if m['role']=='user' and 'Selected target observations' in m['content'])
                    assert question.startswith(model_question(target_request,accepted_evidence))
                    assert accepted_evidence['attachments'][0]['rows']==retained_rows[:2]
                    assert not any(m['role']=='tool' for m in messages)
                    on_text('Synthetic selected-tile response')
                    return {'role':'assistant','content':'Synthetic selected-tile response'}
                async def close(self):self.closed=True
            fake_provider=FixtureProvider()
            dispatch=TargetDispatch(target_queue,target_adapter,lambda _:fake_provider)
            assert dispatch.initialize() is True
            dispatch_wire=(directory/'tile-request.txt').read_bytes()
            task_lane=TargetTasks(TargetAdmission(target_queue,target_adapter),dispatch)
            await task_lane.start(target_request)
            async def settled_task(lane,request):
                async with asyncio.timeout(10):
                    while lane.view(request)['owned_task_active']:await asyncio.sleep(.01)
                return lane.view(request)
            completed_task=await settled_task(task_lane,target_request)
            assert completed_task['turn_status']=='completed' and not completed_task['remote_outcome_unknown']
            assert fake_provider.calls==1 and fake_provider.closed
            assert target_history.turns(target_chat)[0]['status']=='completed'
            assert sum(e['kind']=='user' for e in target_history.events(target_chat))==1
            assert target_adapter.preview(target_chat)==[replacement]
            try:await dispatch.run(target_request)
            except ValueError as error:assert 'already claimed' in str(error)
            else:raise AssertionError('Dispatch repeated an already claimed workflow')
            assert (await task_lane.start(target_request))['turn_status']=='completed'
            assert (await task_lane.close())['pending_owned_tasks']==0
            assert fake_provider.calls==1
            stop_entered=asyncio.Event()
            class PendingFixtureProvider:
                calls=0
                closed=False
                async def complete(self,messages,tools,on_text):
                    self.calls+=1;stop_entered.set();await asyncio.Event().wait()
                async def close(self):self.closed=True
            pending_provider=PendingFixtureProvider()
            stop_chat=target_history.new(snapshot.session_id,model='deepseek-v4-pro')['chat_id']
            stop_request=dict(chat_id=stop_chat,request_id=str(uuid4()),turn_id=str(uuid4()),game_session=snapshot.session_id,
                text='Synthetic backend Stop check; never external inference',attachment_ids=[])
            stop_dispatch=TargetDispatch(target_queue,target_adapter,lambda _:pending_provider)
            stop_lane=TargetTasks(TargetAdmission(target_queue,target_adapter),stop_dispatch)
            await stop_lane.start(stop_request)
            async with asyncio.timeout(10):await stop_entered.wait()
            stop_view=await stop_lane.stop(stop_request)
            assert stop_view['stop_requested'] and stop_view['dispatch_claimed'] and stop_view['remote_outcome_unknown']
            stopped_task=await settled_task(stop_lane,stop_request)
            assert stopped_task['turn_status']=='cancelled' and pending_provider.calls==1 and pending_provider.closed
            assert (await stop_lane.start(stop_request))['turn_status']=='cancelled'
            assert pending_provider.calls==1 and (await stop_lane.close())['pending_owned_tasks']==0
            assert (directory/'tile-request.txt').read_bytes()==dispatch_wire
            target_history.close()
            paid_dispatch=None
            if env_file is not None:
                from dev.verify_target_dispatch_pro import verify as verify_paid_dispatch
                expected_moisture={k:point[k] for k in ('base_fraction','stored_current_fraction')}
                assert replacement['rows'][0]['ground_moisture']['data']==expected_moisture
                paid_dispatch=await verify_paid_dispatch(target_adapter,directory,fresh['capture']['capture_id'],replacement['rows'][0],env_file)
            target_transport_report={'passed':True,'scope':'Developer adapter over actual stdio MCP and copied-city retained tile reads',
                'direct_public_getter_rows_matched':2,'changed_scene_refused':True,'return_to_original_scene_recovers':True,
                'evicted_original_token_refused':True,'explicit_new_capture_selection_passed':True,'failed_draft_preserved':True,'stage_and_prepare_did_not_write_tile_request':True,
                'durable_target_acceptance':{'passed':True,'getter_matched_rows':2,'original_evidence_persisted':True,
                    'queued_question_not_auto_dispatched':True,'queued_survives_store_restart':True,'exact_replay_no_duplicate_turn':True,
                    'old_ack_preserves_restaged_target':True,'tile_mailbox_unchanged':True},
                'explicit_target_dispatch':{'passed':True,'original_evicted_capture_rows_reach_fake_provider':True,
                    'exactly_one_fake_provider_workflow':True,'duplicate_claim_refused':True,
                    'one_original_user_event':True,'newer_draft_preserved':True,'tile_mailbox_unchanged':True},
                'owned_task_stop':{'passed':True,'completed_getter_backed_workflow':True,
                    'exact_start_replay_no_new_provider_call':True,'running_fake_provider_stop':True,
                    'terminal_cancelled_and_cleanup_finished':True,'unknown_remote_outcome_kept_explicit':True},
                'native_player_picker_or_send_integration':False,'inference_calls':0,
                'source_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in
                    ['dev/chat_target_candidate.py','dev/chat_target_transport.py','dev/chat_target_queue.py','dev/chat_target_dispatch.py','dev/chat_target_tasks.py','dev/verify_tiles.py']}}
            tile_capture_report={'paid_target_dispatch':paid_dispatch,'passed':True,'developer_target_transport':target_transport_report,'game_version':snapshot.game_version,'retained_rows':len(captured),
                'retained_pages':retained_pages,'direct_public_getter_row_parity':True,'ground_moisture_live_and_retained_parity':True,'ground_moisture_retained_rows':100,'ground_moisture_retained_pages':10,'wide_100_row_tool_text_budget_refusal':True,'original_request_tick_time_scene_and_ui_preserved':True,
                'active_simulation_and_view_change':True,'paging_did_not_write_game_request_mailbox':True,
                'complete_empty_selection_scanned_tiles':4096,'incomplete_row_cap_rejected':True,'concurrent_pages':True,
                'wrong_kind_token_rejected':True,'help_discoverable':True,'snapshot_tile_field_list_matches_moisture_support':True,
                'inference_calls':0 if paid_dispatch is None else paid_dispatch['provider_round_attempts'],
                'controlled_fixture_actions':['VIEW.world().activate()','VIEW.s().activate()','GAME.SPEED.speedSet(...)'],
                'source_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in
                    ['syx_capture.py','syx_tiles.py','syx_mcp.py','mod/tests/TileScenario.java','dev/verify_tiles.py']},
                'limits':['Copied city; at most 4096 scanned tiles, 100 matches and 64 KiB. No full-map/large-city latency or all-field/all-scene capture acceptance.',
                    'Field getter failures remain explicit unknowns; synthetic tests separately cover predicate-error, byte, expiry and eviction failures.',
                    'No global worker transaction, UI-selected room, route/construction or complete game-state claim.',
                    'Only the copied fixture changes view/speed. Production capture/read tools remain read-only and never pause or control the game.']}
            print('PASS retained 100-tile public getter parity, ten pages after simulation/view change, empty 4096-tile capture and incomplete-row refusal',flush=True)
            report={'passed':True,'game_version':'0.71.44','point_cases':len(fixture['points']),
                'case_labels':[v['case'] for v in fixture['points']], 'pages':pages,'matching_tiles':len(rows),
                'field_parity':True,'null_presence_distinguished':True,'combined_filters':True,
                'mineral_installed_reference':True,'coordinate_and_cursor_bounds':True,'concurrent_tile_entity_requests':True,
                'mcp_text_cap_checked':True,'observer_phase':'GAME.addAfterUpdate',
                'limits':['Copied paused city; cursor pages remain separate mutable observations.',
                    'Scene follow-up covers city/tactical HUD/generated deployment/menu/reload/initial and terrain world setup; not active combat or every menu.',
                    'Room map record IDs can be shared; no UI-selected room, construction suitability, particular-agent route or yield forecast established.']}
            (directory/'tile-validation.json').write_text(json.dumps(report,indent=2)+'\n')
            (directory/'tile-verifier.done').write_text('passed\n')
            scenes=asyncio.create_task(asyncio.to_thread(verify_scenes,directory,220,True,True))
            began=time.monotonic()
            while time.monotonic()-began<110:
                if advisor.snapshot().session_id!=fresh['capture']['session_id']:break
                await asyncio.sleep(.2)
            else:raise AssertionError('No copied-game session rotation before retained-token expiry')
            await tool('read_tile_capture',{'capture_id':fresh['capture']['capture_id']},error='session/version')
            tile_capture_report['actual_session_rotation_invalidates_token']=True
            await scenes
            (directory/'tile-capture-validation.json').write_text(json.dumps(tile_capture_report,indent=2)+'\n')
            return tile_capture_report
    # The fixture advances through public scene tests while the original MCP token store stays alive.


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--state-dir',type=Path,required=True)
    parser.add_argument('--env-file',type=Path,help='Explicitly enable two paid Pro developer handoff turns')
    args=parser.parse_args()
    asyncio.run(verify(args.state_dir,args.env_file))
