"""Explicit accepted-turn handoff: real MCP transport, fake inference only."""
import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from uuid import uuid4

import pytest
from mcp import ClientSession
from mcp.client.stdio import stdio_client
from syx_chat_store import ChatStore
from dev.chat_target_queue import TargetQueue, TargetAdmission
from dev.chat_target_transport import McpTargetDrafts
from dev.chat_target_dispatch import TargetDispatch, model_question
from test_chat_target_transport import transport_state, parameters, create
from test_syx_chat import Provider, answer, tool


@asynccontextmanager
async def harness(path, state, directory, provider):
    store = ChatStore(directory, secrets=('never-emit-this-test-key',))
    try:
        queue=TargetQueue(store);queue.initialize()
        cid=store.new(state['session_id'],model='deepseek-v4-pro')['chat_id']
        async with stdio_client(parameters(path)) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize();token=await create(session)
                adapter=McpTargetDrafts(session);item=await adapter.stage(cid,'entity',token)
                request=dict(chat_id=cid,request_id=str(uuid4()),turn_id=str(uuid4()),game_session=state['session_id'],
                             text='Explain the selected person',attachment_ids=[item['attachment_id']])
                await TargetAdmission(queue,adapter).accept(**request)
                dispatch=TargetDispatch(queue,adapter,lambda _:provider);dispatch.initialize()
                yield dispatch,queue,store,request,adapter
    finally:store.close()


def status(store, request): return store.turns(request['chat_id'])[0]['status']

def test_original_question_and_targets_reach_unchanged_loop_without_duplicate_user_event(transport_state,tmp_path):
    path,state=transport_state
    async def run():
        provider=Provider([tool('game_status','{}'),answer('Observed person answer')]);visible=[]
        async with harness(path,state,tmp_path/'handoff',provider) as (dispatch,queue,store,request,adapter):
            original=queue.accepted_evidence(request['request_id'])
            # Chips may already be acknowledged; dispatch uses original durable data.
            await TargetAdmission(queue,adapter).acknowledge(request)
            assert await dispatch.run(request,visible.append)=='Observed person answer'
            assert provider.closed and len(provider.messages)==2 and status(store,request)=='completed'
            user=next(m for m in provider.messages[0] if m['role']=='user' and 'Selected target observations' in m['content'])
            assert user['content'].startswith(model_question(request,original))
            assert 'untrusted historical data' in user['content']
            events=store.events(request['chat_id'])
            assert [e['kind'] for e in events].count('user')==1
            assert next(e for e in events if e['kind']=='user')['payload']['text']==request['text']
            assert next(e for e in events if e['kind']=='target_evidence')['payload']['envelope']==original
            assert sum(e['kind']=='dispatch_claimed' for e in events)==1
            assert 'hidden' not in json.dumps(events)
            with pytest.raises(ValueError,match='already claimed'):await dispatch.run(request)
            assert len(provider.messages)==2
            store.delete(request['chat_id'])
            assert store.db.execute('SELECT count(*) FROM syx_target_dispatch').fetchone()[0]==0
            assert store.db.execute('PRAGMA foreign_key_check').fetchall()==[]
    asyncio.run(run())


@pytest.mark.parametrize('change',['runtime','scene','version','age','route','attachment','cancelled','intent','lease'])
def test_preclaim_refusal_is_queued_and_never_infers(transport_state,tmp_path,change):
    path,state=transport_state
    async def run():
        provider=Provider([answer('must not run')])
        async with harness(path,state,tmp_path/'refusal',provider) as (dispatch,queue,store,request,adapter):
            real=adapter._status
            async def changed():
                current=await real()
                if change=='runtime':current['session_id']=str(uuid4())
                if change=='scene':current['scene']['active_view']='world'
                if change=='version':current['game_version']='different'
                if change=='age':current['captured_at']=(datetime.now(timezone.utc)-timedelta(seconds=31)).isoformat()
                return current
            adapter._status=changed
            if change=='route':
                store.db.execute("UPDATE chats SET model='deepseek-flash'");store.db.commit()
            if change=='attachment':store.attach(request['chat_id'],str(uuid4()))
            if change=='cancelled':queue.cancel(request)
            if change=='intent':request['text']='changed after acceptance'
            if change=='lease':
                ticks=iter([10,12]);dispatch.clock=lambda:next(ticks)
            with pytest.raises(ValueError):await dispatch.run(request)
            assert provider.messages==[] and not provider.closed
            assert status(store,request)==('cancelled' if change=='cancelled' else 'queued')
            assert store.db.execute('SELECT count(*) FROM syx_target_dispatch').fetchone()[0]==0
    asyncio.run(run())


def test_claim_transaction_failure_rolls_back_to_queued_without_inference(transport_state,tmp_path):
    path,state=transport_state
    async def run():
        provider=Provider([answer('must not run')])
        async with harness(path,state,tmp_path/'rollback',provider) as (dispatch,queue,store,request,_):
            store.db.execute("CREATE TRIGGER refuse_claim BEFORE INSERT ON events WHEN NEW.kind='dispatch_claimed' BEGIN SELECT RAISE(ABORT,'test failure'); END")
            store.db.commit()
            with pytest.raises(Exception):await dispatch.run(request)
            assert status(store,request)=='queued' and len(store.events(request['chat_id']))==2
            assert not provider.messages and store.db.execute('SELECT count(*) FROM syx_target_dispatch').fetchone()[0]==0
    asyncio.run(run())


@pytest.mark.parametrize('when',['preclaim','provider','completed_before_result'])
def test_cancellation_and_uncertain_network_never_replay_after_restart(transport_state,tmp_path,when):
    path,state=transport_state
    async def run():
        entered=asyncio.Event();hold=asyncio.Event()
        class Blocking(Provider):
            async def complete(self,messages,tools,on_text):
                self.messages.append(deepcopy(messages));entered.set()
                if when=='completed_before_result':
                    on_text('partial visible result')
                    raise ConnectionError('remote may have billed; never-emit-this-test-key')
                await hold.wait()
        provider=Blocking([])
        async with harness(path,state,tmp_path/'cancel',provider) as (dispatch,queue,store,request,adapter):
            if when=='preclaim':
                real=adapter._status
                async def block():entered.set();await hold.wait();return await real()
                adapter._status=block
            task=asyncio.create_task(dispatch.run(request));await entered.wait()
            if when!='completed_before_result':task.cancel()
            with pytest.raises((asyncio.CancelledError,ConnectionError)):await task
            assert status(store,request)==('queued' if when=='preclaim' else 'cancelled' if when=='provider' else 'failed')
            assert len(provider.messages)==(0 if when=='preclaim' else 1)
            assert 'never-emit-this-test-key' not in json.dumps(store.events(request['chat_id']))
            reopened=ChatStore(store.directory,recover=True)
            try:
                retry=TargetDispatch(TargetQueue(reopened),adapter,lambda _:provider);assert retry.initialize() is False
                if when!='preclaim':
                    with pytest.raises(ValueError,match='already claimed'):await retry.run(request)
                assert status(reopened,request)==status(store,request)
            finally:reopened.close()
    asyncio.run(run())


def test_two_coordinators_only_one_claim_and_crashed_running_turn_is_interrupted(transport_state,tmp_path):
    path,state=transport_state
    async def run():
        provider=Provider([answer('only once')])
        async with harness(path,state,tmp_path/'concurrent',provider) as (dispatch,queue,store,request,adapter):
            other=ChatStore(store.directory)
            try:
                rival=TargetDispatch(TargetQueue(other),adapter,lambda _:provider);rival.initialize()
                results=await asyncio.gather(dispatch.run(request),rival.run(request),return_exceptions=True)
                assert sum(r=='only once' for r in results)==1 and sum(isinstance(r,ValueError) for r in results)==1
                assert len(provider.messages)==1
                # Simulate abrupt death after commit, before Conversation can finalize.
                store.db.execute("UPDATE turns SET status='running'");store.db.commit()
            finally:other.close()
            recovered=ChatStore(store.directory,recover=True)
            try:
                retry=TargetDispatch(TargetQueue(recovered),adapter,lambda _:provider)
                assert status(recovered,request)=='interrupted'
                with pytest.raises(ValueError,match='already claimed'):await retry.run(request)
                assert len(provider.messages)==1
            finally:recovered.close()
    asyncio.run(run())


@pytest.mark.parametrize('damage',['unknown','unversioned'])
def test_dispatch_schema_refuses_unknown_and_unversioned(transport_state,tmp_path,damage):
    path,state=transport_state
    async def run():
        provider=Provider([])
        async with harness(path,state,tmp_path/'schema',provider) as (dispatch,_,store,_,_):
            if damage=='unknown':store.db.execute("UPDATE syx_ux_schema SET version=2 WHERE component='target_dispatch'")
            else:store.db.execute("DELETE FROM syx_ux_schema WHERE component='target_dispatch'")
            store.db.commit()
            with pytest.raises(ValueError):dispatch.initialize()
            assert not provider.messages
    asyncio.run(run())


@pytest.mark.parametrize('failure',['tool_listing','runtime_recheck','provider_factory'])
def test_failure_after_claim_before_inference_consumes_claim_without_replay(transport_state,tmp_path,failure):
    path,state=transport_state
    async def run():
        provider=Provider([answer('must not run')])
        async with harness(path,state,tmp_path/'claimed-failure',provider) as (dispatch,queue,store,request,adapter):
            if failure=='tool_listing':
                async def failed_listing():raise ConnectionError('lost MCP')
                adapter._session.list_tools=failed_listing  # adapter already admitted at acceptance
            elif failure=='runtime_recheck':
                real=adapter._status
                async def preflight_then_disconnect():
                    result=await real()
                    original=adapter._session.call_tool
                    async def changed(name,args,**kw):
                        if name=='game_status':raise ConnectionError('lost status')
                        return await original(name,args,**kw)
                    adapter._session.call_tool=changed
                    return result
                adapter._status=preflight_then_disconnect
            else:
                def unavailable(_):raise ValueError('No explicit provider supplied')
                dispatch.provider_factory=unavailable
            with pytest.raises((ValueError,ConnectionError)):await dispatch.run(request)
            assert status(store,request)=='failed' and not provider.messages
            with pytest.raises(ValueError,match='already claimed'):await dispatch.run(request)
    asyncio.run(run())


def test_mutating_caller_selection_while_preflight_waits_does_not_change_accepted_evidence(transport_state,tmp_path):
    path,state=transport_state
    async def run():
        provider=Provider([answer('original intent')])
        async with harness(path,state,tmp_path/'frozen',provider) as (dispatch,queue,store,request,adapter):
            entered=asyncio.Event();release=asyncio.Event();real=adapter._status
            original=deepcopy(request)
            async def blocked():entered.set();await release.wait();return await real()
            adapter._status=blocked
            task=asyncio.create_task(dispatch.run(request));await entered.wait()
            request['attachment_ids'].clear();request['text']='unaccepted new question'
            release.set();assert await task=='original intent'
            content=next(m['content'] for m in provider.messages[0] if 'Selected target observations' in m.get('content',''))
            assert content.startswith(original['text']) and original['attachment_ids'][0] in content
            assert 'unaccepted new question' not in content
    asyncio.run(run())


def test_claim_refuses_an_existing_running_turn_from_another_lane(transport_state,tmp_path):
    path,state=transport_state
    async def run():
        provider=Provider([answer('must not run')])
        async with harness(path,state,tmp_path/'busy-chat',provider) as (dispatch,queue,store,request,_):
            # A legacy lane can begin outside queue admission; claim must recheck.
            legacy=str(uuid4());store.begin(request['chat_id'],legacy,request['game_session'],'Legacy question')
            with pytest.raises(ValueError,match='Another reply'):await dispatch.run(request)
            assert store.turns(request['chat_id'])[0]['status']=='queued' and not provider.messages
            store.finish(request['chat_id'],legacy,'cancelled')
            assert await dispatch.run(request)=='must not run'
    asyncio.run(run())


def test_newly_registered_secret_in_older_accepted_data_refuses_inference(transport_state,tmp_path):
    path,state=transport_state
    async def run():
        provider=Provider([answer('must not run')])
        async with harness(path,state,tmp_path/'new-secret',provider) as (dispatch,_,store,request,_):
            # An accepted historical value can become a known credential later.
            store.secrets=store.secrets+('selected person',)
            with pytest.raises(ValueError,match='currently registered credential'):await dispatch.run(request)
            assert status(store,request)=='queued' and not provider.messages
            assert store.db.execute('SELECT count(*) FROM syx_target_dispatch').fetchone()[0]==0
    asyncio.run(run())
