"""Automatic current-game connection uses fresh MCP evidence, never caller UUID alone."""
import asyncio
import json

import pytest

from syx_chat_service import Coordinator, action, unb64
from syx_chat_store import ChatStore
from test_syx_chat import MCP, Provider, answer, uid


def test_sync_opens_one_pro_chat_and_reuses_current_load_history(tmp_path):
    async def scenario():
        session = uid()
        store = ChatStore(tmp_path/'history')
        older = store.new(uid(), 'Different load', model='deepseek-v4-pro')
        coordinator = Coordinator(store, MCP(session), tmp_path, '', simple=True)
        for _ in range(2):
            await coordinator.dispatch(dict(protocol='2', request_id=uid(), action='sync', session_id=session))
        current = store.chat(coordinator.selected)
        assert current['attached_session'] == session and current['model'] == 'deepseek-v4-pro'
        assert len(store.list()) == 2 and store.chat(older['chat_id']) == older
        coordinator.selected = None
        await coordinator.dispatch(dict(protocol='2', request_id=uid(), action='sync', session_id=session))
        assert coordinator.selected == current['chat_id'] and len(store.list()) == 2
        assert not coordinator.tasks and not store.turns(current['chat_id'])
        store.close()
    asyncio.run(scenario())


def test_question_reconnects_after_reload_with_history_and_provider_reset(tmp_path):
    async def scenario():
        old, new = uid(), uid()
        store = ChatStore(tmp_path/'history')
        mcp = MCP(old)
        coordinator = Coordinator(store, mcp, tmp_path, 'fixture-key', simple=True)
        providers = [Provider([answer('First answer')]), Provider([answer('Second answer')])]
        coordinator.loop.provider_factory = lambda _: providers.pop(0)
        await coordinator.dispatch(dict(protocol='2', request_id=uid(), action='sync', session_id=old))
        cid = coordinator.selected
        await coordinator.dispatch(dict(request_id=uid(), action='send', session_id=old, chat_id=cid, text='First question'))
        await coordinator.tasks[cid]
        before = store.events(cid)
        mcp.session = new
        await coordinator.dispatch(dict(protocol='2', request_id=uid(), action='sync', session_id=new))
        assert store.chat(cid)['attached_session'] == old  # no in-flight/implicit background transfer
        second = providers[0]
        request = dict(request_id=uid(), action='send', session_id=new, chat_id=cid, text='Next question')
        await coordinator.dispatch(request)
        await coordinator.tasks[cid]
        await coordinator.dispatch(request)  # a replay never sends another paid turn
        assert [t['game_session'] for t in store.turns(cid)] == [old, new]
        assert all(t['status'] == 'completed' for t in store.turns(cid))
        assert store.events(cid)[:len(before)] == before
        boundaries = [e for e in store.events(cid) if e['kind'] == 'session_boundary']
        assert len(boundaries) == 1 and boundaries[0]['payload']['automatic_current_game'] is True
        assert boundaries[0]['payload']['explicit_continuation'] is False
        assert len([e for e in store.events(cid) if e['kind'] == 'context_reset']) == 2
        assert not any(m['role'] == 'assistant' for m in second.messages[0])
        assert 'First answer' in second.messages[0][1]['content']
        coordinator.write_ui()
        raw = (tmp_path/'chat-ui.txt').read_text()
        visible = [unb64(x[5:]) for x in raw.splitlines() if x.startswith('line=')]
        assert 'Earlier game · Assistant: First answer' in visible
        assert 'Assistant: Second answer' in visible
        assert 'protocol=2\n' in raw and 'current_chat_session='+new in raw
        store.close()
    asyncio.run(scenario())


@pytest.mark.parametrize('bad', ['stale', 'unloaded', 'different', 'tool-error', 'timeout'])
def test_no_reconnection_or_inference_without_matching_live_observation(tmp_path, bad):
    async def scenario():
        old, new = uid(), uid()
        store = ChatStore(tmp_path/'history')
        c = store.new(old, model='deepseek-v4-pro')
        coordinator = Coordinator(store, MCP(new), tmp_path, 'fixture-key', simple=True)
        async def observation(*_):
            if bad == 'timeout':raise TimeoutError()
            status = dict(session_id=new, fresh=True, live=True)
            if bad == 'stale':status['fresh'] = False
            if bad == 'unloaded':status['live'] = False
            if bad == 'different':status['session_id'] = uid()
            return {'error':'unavailable'} if bad == 'tool-error' else {'structuredContent':status}
        coordinator.loop._tool = observation
        with pytest.raises(ValueError, match='no question was sent'):
            await coordinator.dispatch(dict(request_id=uid(), action='send', session_id=new, chat_id=c['chat_id'], text='Question'))
        assert store.chat(c['chat_id']) == c and not store.events(c['chat_id'])
        assert not store.turns(c['chat_id']) and not coordinator.tasks
        store.close()
    asyncio.run(scenario())


def test_running_reply_and_missing_key_cannot_transfer_chat(tmp_path):
    async def scenario():
        old, new = uid(), uid()
        store = ChatStore(tmp_path/'history')
        c = store.new(old, model='deepseek-v4-pro')
        coordinator = Coordinator(store, MCP(new), tmp_path, '', simple=True)
        request = dict(request_id=uid(), action='send', session_id=new, chat_id=c['chat_id'], text='Question')
        with pytest.raises(ValueError, match='key is missing'):
            await coordinator.dispatch(request)
        coordinator.key = 'fixture-key'
        pending = asyncio.create_task(asyncio.Event().wait())
        coordinator.tasks[c['chat_id']] = pending
        with pytest.raises(ValueError, match='already running'):
            await coordinator.dispatch(dict(request, request_id=uid()))
        assert store.chat(c['chat_id']) == c and not store.events(c['chat_id'])
        pending.cancel()
        try:await pending
        except asyncio.CancelledError:pass
        store.close()
    asyncio.run(scenario())


def test_filtered_current_list_is_not_hidden_by_the_global_hundred_chat_cap(tmp_path):
    session = uid()
    store = ChatStore(tmp_path/'history')
    current = store.new(session, 'Older current chat', model='deepseek-v4-pro')
    for _ in range(105):store.new(uid(), model='deepseek-v4-pro')
    for _ in range(105):store.new(session, 'Flash history')
    coordinator = Coordinator(store, MCP(session), tmp_path, '', simple=True)
    coordinator.ui_session = session
    coordinator.write_ui()
    raw = (tmp_path/'chat-ui.txt').read_text()
    assert len([x for x in raw.splitlines() if x.startswith('chat=')]) == 100
    assert [x.split('|')[0] for x in raw.splitlines() if x.startswith('current_chat=')] == ['current_chat='+current['chat_id']]
    assert 'Flash history' not in '\n'.join(unb64(x.split('|')[1]) for x in raw.splitlines() if x.startswith(('chat=', 'current_chat=')))
    store.close()


def test_sync_requires_paired_protocol(tmp_path):
    session, rid = uid(), uid()
    raw = f'protocol=2\nrequest_id={rid}\naction=sync\nsession_id={session}\n'.encode()
    assert action(raw)['action'] == 'sync'
    for bad in [raw.replace(b'protocol=2\n', b''), raw.replace(b'protocol=2', b'protocol=3')]:
        with pytest.raises(ValueError):action(bad)


def test_parallel_admission_does_not_start_two_replies(tmp_path):
    async def scenario():
        session = uid()
        store = ChatStore(tmp_path/'history')
        c = store.new(session, model='deepseek-v4-pro')
        coordinator = Coordinator(store, MCP(session), tmp_path, 'fixture-key', simple=True)
        original = coordinator.current_game
        async def delayed(s):
            await asyncio.sleep(0)
            return await original(s)
        coordinator.current_game = delayed
        gate = asyncio.Event()
        class Pending(Provider):
            async def complete(self, *args):
                await gate.wait()
                return answer('Done')
        coordinator.loop.provider_factory = lambda _:Pending([])
        request = dict(action='send', session_id=session, chat_id=c['chat_id'], text='Question')
        results = await asyncio.gather(*(coordinator.dispatch(dict(request, request_id=uid())) for _ in range(2)), return_exceptions=True)
        assert sum(isinstance(r, ValueError) for r in results) == 1
        gate.set()
        await coordinator.tasks[c['chat_id']]
        assert len(store.turns(c['chat_id'])) == 1
        store.close()
    asyncio.run(scenario())
