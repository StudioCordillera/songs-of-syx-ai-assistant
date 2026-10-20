"""Real stdio read-only MCP, disposable histories, owned tasks and fake providers."""
import asyncio
from copy import deepcopy
from uuid import uuid4
import pytest
from syx_chat_store import ChatStore
from dev.chat_target_queue import TargetQueue, TargetAdmission
from dev.chat_target_dispatch import TargetDispatch
from dev.chat_target_tasks import TargetTasks
from test_chat_target_dispatch import harness
from test_chat_target_transport import transport_state
from test_syx_chat import Provider, answer


async def settled(lane, request):
    async with asyncio.timeout(3):
        while request['request_id'] in lane._active: await asyncio.sleep(.005)
    return lane.view(request)


class Blocking(Provider):
    def __init__(self, *, hold_close=False):
        super().__init__([])
        self.entered=asyncio.Event();self.release=asyncio.Event()
        self.close_entered=asyncio.Event();self.close_release=asyncio.Event()
        self.close_cancelled=False;self.hold_close=hold_close
    async def complete(self,messages,tools,on_text):
        self.messages.append(deepcopy(messages));self.entered.set();await self.release.wait()
        on_text('Completed owned reply');return answer('Completed owned reply')
    async def close(self):
        self.close_entered.set()
        try:
            if self.hold_close:await self.close_release.wait()
        except asyncio.CancelledError:self.close_cancelled=True;raise
        self.closed=True


def test_immediate_stop_before_coroutine_starts_cancels_queued_turn_without_inference(transport_state,tmp_path):
    path,state=transport_state
    async def run():
        provider=Blocking()
        async with harness(path,state,tmp_path/'immediate',provider) as (dispatch,queue,store,request,adapter):
            lane=TargetTasks(TargetAdmission(queue,adapter),dispatch)
            initial=await lane.start(request);assert initial['owned_task_active'] and initial['turn_status']=='queued'
            stopped=await lane.stop(request)
            assert stopped['stop_requested'] and stopped['turn_status']=='cancelled' and not stopped['dispatch_claimed']
            final=await settled(lane,request)
            assert not final['remote_outcome_unknown'] and not provider.messages
            assert len(store.events(request['chat_id']))==3
            assert adapter.preview(request['chat_id'])  # Stop is not chip acknowledgement
            assert (await lane.close())['pending_owned_tasks']==0
    asyncio.run(run())


def test_stop_is_exact_idempotent_and_does_not_recancel_provider_cleanup(transport_state,tmp_path):
    path,state=transport_state
    async def run():
        provider=Blocking(hold_close=True)
        async with harness(path,state,tmp_path/'stop',provider) as (dispatch,queue,store,request,adapter):
            lane=TargetTasks(TargetAdmission(queue,adapter),dispatch)
            await lane.start(request);await provider.entered.wait()
            wrong=dict(request,text='different intent')
            with pytest.raises(ValueError,match='different send'):await lane.stop(wrong)
            await lane.stop(request);await provider.close_entered.wait()
            again=await lane.stop(request)
            assert again['turn_status']=='cancelled' and again['cleanup_pending'] and again['remote_outcome_unknown']
            assert not provider.close_cancelled
            provider.close_release.set();final=await settled(lane,request)
            assert not final['owned_task_active'] and final['last_attempt']=='cancelled'
            assert len(provider.messages)==1 and provider.closed
            assert (await lane.start(request))['turn_status']=='cancelled'
            assert len(provider.messages)==1
            await lane.close()
    asyncio.run(run())


def test_completed_reply_and_pending_cleanup_cannot_be_changed_by_stop(transport_state,tmp_path):
    path,state=transport_state
    async def run():
        provider=Blocking(hold_close=True)
        async with harness(path,state,tmp_path/'completion',provider) as (dispatch,queue,store,request,adapter):
            lane=TargetTasks(TargetAdmission(queue,adapter),dispatch)
            await lane.start(request);await provider.entered.wait();provider.release.set()
            await provider.close_entered.wait()
            view=await lane.stop(request)
            assert view['turn_status']=='completed' and view['cleanup_pending'] and not view['stop_requested']
            assert not view['remote_outcome_unknown'] and not provider.close_cancelled
            provider.close_release.set();view=await settled(lane,request)
            assert view['last_attempt']=='returned'
            await lane.start(request);assert len(provider.messages)==1
            await lane.close()
    asyncio.run(run())


def test_concurrent_exact_starts_and_mutable_caller_ids_only_schedule_once(transport_state,tmp_path):
    path,state=transport_state
    async def run():
        provider=Blocking()
        async with harness(path,state,tmp_path/'duplicate',provider) as (dispatch,queue,store,request,adapter):
            lane=TargetTasks(TargetAdmission(queue,adapter),dispatch)
            first,second=await asyncio.gather(lane.start(request),lane.start(request))
            assert first['accepted'] and second['accepted']
            await provider.entered.wait();assert len(provider.messages)==1
            original=deepcopy(request);request['attachment_ids'].clear();request['text']='changed caller'
            await lane.stop(original);await settled(lane,original)
            assert len(store.turns(original['chat_id']))==1
            await lane.close()
    asyncio.run(run())


def test_close_during_acceptance_waits_then_cancels_before_any_provider(transport_state,tmp_path):
    path,state=transport_state
    async def run():
        provider=Blocking()
        async with harness(path,state,tmp_path/'close-race',provider) as (dispatch,queue,store,request,adapter):
            request=dict(request,chat_id=store.new(state['session_id'],model='deepseek-v4-pro')['chat_id'],
                         request_id=str(uuid4()),turn_id=str(uuid4()),attachment_ids=[])
            admission=TargetAdmission(queue,adapter);lane=TargetTasks(admission,dispatch)
            entered=asyncio.Event();release=asyncio.Event();real=admission.accept
            async def blocked(**args):entered.set();await release.wait();return await real(**args)
            admission.accept=blocked
            starting=asyncio.create_task(lane.start(request));await entered.wait()
            closing=asyncio.create_task(lane.close());await asyncio.sleep(0)
            assert not closing.done()
            release.set()
            with pytest.raises(ValueError,match='closed during acceptance'):await starting
            assert (await closing)=={'closed':True,'pending_owned_tasks':0}
            assert lane.view(request)['turn_status']=='cancelled' and not provider.messages
            with pytest.raises(ValueError,match='closed'):await lane.start(request)
    asyncio.run(run())


def test_overload_refuses_before_acceptance_and_close_keeps_slow_cleanup_owned(transport_state,tmp_path):
    path,state=transport_state
    async def run():
        provider=Blocking(hold_close=True)
        async with harness(path,state,tmp_path/'bounds',provider) as (dispatch,queue,store,request,adapter):
            lane=TargetTasks(TargetAdmission(queue,adapter),dispatch);lane.MAX_ACTIVE=1
            await lane.start(request);await provider.entered.wait()
            other=dict(request,chat_id=store.new(state['session_id'],model='deepseek-v4-pro')['chat_id'],
                       request_id=str(uuid4()),turn_id=str(uuid4()),attachment_ids=[])
            with pytest.raises(ValueError,match='full'):await lane.start(other)
            assert queue.lookup(other) is None and store.events(other['chat_id'])==[]
            result=await lane.close()
            assert result['pending_owned_tasks']==1 and lane.view(request)['cleanup_pending']
            assert not provider.close_cancelled
            provider.close_release.set();await settled(lane,request)
            assert (await lane.close())['pending_owned_tasks']==0
    asyncio.run(run())


def test_restart_and_unowned_task_views_never_resume_or_cancel_another_owner(transport_state,tmp_path):
    path,state=transport_state
    async def run():
        provider=Blocking()
        async with harness(path,state,tmp_path/'ownership',provider) as (dispatch,queue,store,request,adapter):
            lane=TargetTasks(TargetAdmission(queue,adapter),dispatch)
            await lane.start(request);await provider.entered.wait()
            other=ChatStore(store.directory)
            try:
                otherq=TargetQueue(other);otherd=TargetDispatch(otherq,adapter,lambda _:provider)
                outsider=TargetTasks(TargetAdmission(otherq,adapter),otherd)
                view=await outsider.stop(request)
                assert view['turn_status']=='running' and not view['owned_task_active'] and not view['stop_requested']
                await outsider.start(request);assert len(provider.messages)==1
                await lane.stop(request);await settled(lane,request)
                assert (await outsider.start(request))['turn_status']=='cancelled'
                assert len(provider.messages)==1
                await outsider.close()
            finally:other.close()
            await lane.close()
    asyncio.run(run())


def test_failed_preclaim_attempt_stays_queued_and_only_explicit_start_retries(transport_state,tmp_path):
    path,state=transport_state
    async def run():
        provider=Provider([answer('Explicit retry answer')])
        async with harness(path,state,tmp_path/'preclaim',provider) as (dispatch,queue,store,request,adapter):
            lane=TargetTasks(TargetAdmission(queue,adapter),dispatch);real=adapter._status
            async def unavailable():raise ValueError('No fresh current scene')
            adapter._status=unavailable
            await lane.start(request);view=await settled(lane,request)
            assert view['turn_status']=='queued' and view['last_attempt']=='failed' and not view['dispatch_claimed']
            assert not provider.messages
            adapter._status=real
            assert not lane.view(request)['owned_task_active']  # no automatic retry on reconnect
            await lane.start(request);view=await settled(lane,request)
            assert view['turn_status']=='completed' and len(provider.messages)==1
            assert len(store.turns(request['chat_id']))==1
            await lane.close()
    asyncio.run(run())


def test_start_cancelled_during_admission_never_schedules_or_clears_drafts(transport_state,tmp_path):
    path,state=transport_state
    async def run():
        provider=Blocking()
        async with harness(path,state,tmp_path/'cancel-start',provider) as (dispatch,queue,store,request,adapter):
            admission=TargetAdmission(queue,adapter);lane=TargetTasks(admission,dispatch);entered=asyncio.Event()
            async def blocked(**args):entered.set();await asyncio.Event().wait()
            admission.accept=blocked
            task=asyncio.create_task(lane.start(request));await entered.wait();task.cancel()
            with pytest.raises(asyncio.CancelledError):await task
            view=lane.view(request)
            assert view['turn_status']=='queued' and not view['owned_task_active'] and not view['dispatch_claimed']
            assert adapter.preview(request['chat_id']) and not provider.messages
            await lane.close()
    asyncio.run(run())


def test_stop_can_cancel_owned_queued_preclaim_failure_without_retry(transport_state,tmp_path):
    path,state=transport_state
    async def run():
        provider=Blocking()
        async with harness(path,state,tmp_path/'orphan',provider) as (dispatch,queue,store,request,adapter):
            lane=TargetTasks(TargetAdmission(queue,adapter),dispatch)
            async def unavailable():raise ValueError('No fresh scene')
            adapter._status=unavailable
            await lane.start(request);await settled(lane,request)
            stopped=await lane.stop(request)
            assert stopped['turn_status']=='cancelled' and not stopped['dispatch_claimed']
            assert (await lane.start(request))['turn_status']=='cancelled' and not provider.messages
            await lane.close()
    asyncio.run(run())


def test_close_cancels_remaining_owned_tasks_when_one_history_record_was_deleted(transport_state,tmp_path):
    path,state=transport_state
    async def run():
        first=Blocking();second=Blocking()
        async with harness(path,state,tmp_path/'deleted',first) as (dispatch,queue,store,request,adapter):
            peers=iter([first,second]);dispatch.provider_factory=lambda _:next(peers)
            lane=TargetTasks(TargetAdmission(queue,adapter),dispatch)
            await lane.start(request);await first.entered.wait()
            other=dict(request,chat_id=store.new(state['session_id'],model='deepseek-v4-pro')['chat_id'],
                       request_id=str(uuid4()),turn_id=str(uuid4()),attachment_ids=[])
            await lane.start(other);await second.entered.wait()
            store.delete(request['chat_id'])
            assert (await lane.close())['pending_owned_tasks']==0
            assert first.closed and second.closed
            assert lane.view(other)['turn_status']=='cancelled'
            assert not lane._active
    asyncio.run(run())


def test_stop_after_preclaim_task_done_before_callback_still_cancels_queued_turn(transport_state,tmp_path):
    path,state=transport_state
    async def run():
        provider=Blocking()
        async with harness(path,state,tmp_path/'done-callback-gap',provider) as (dispatch,queue,store,request,adapter):
            async def immediate_failure(*args,**kwargs):raise ValueError('Before claim')
            dispatch.run=immediate_failure
            lane=TargetTasks(TargetAdmission(queue,adapter),dispatch)
            await lane.start(request);await asyncio.sleep(0)
            assert lane._active[request['request_id']]['task'].done()
            assert request['request_id'] not in lane._recent
            assert (await lane.stop(request))['turn_status']=='cancelled'
            assert not provider.messages
            await lane.close()
    asyncio.run(run())
