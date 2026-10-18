import asyncio
import json
import stat
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from mcp.types import CallToolResult, TextContent, Tool, ToolAnnotations
from syx_chat import Conversation, TOOLS
from syx_chat_store import ChatStore
from syx_deepseek import DeepSeek, ProviderError


def uid():return str(uuid4())


def run(coro):return asyncio.run(coro)


def test_history_isolation_recovery_and_redaction(tmp_path):
    store=ChatStore(tmp_path/'history',secrets=['private-key'])
    session=uid();a=store.new(session,'A');b=store.new(session,'B');turn=uid()
    store.begin(a['chat_id'],turn,session,'question')
    store.append(a['chat_id'],turn,session,'assistant',{'text':'private-key answer','reasoning_content':'SECRET','api_key':'private-key'})
    assert store.events(b['chat_id'])==[]
    event=store.events(a['chat_id'])[-1]
    assert event['payload']=={'text':'[credential redacted] answer','provider':'deepseek','model':'deepseek-flash','route':'api'}
    with pytest.raises(ValueError,match='already exists'):store.begin(a['chat_id'],turn,session,'retry')
    with pytest.raises(Exception):store.append(b['chat_id'],turn,session,'assistant',{'text':'cross-chat'})
    assert stat.S_IMODE((tmp_path/'history'/'history.sqlite3').stat().st_mode)==0o600
    store.close()
    store=ChatStore(tmp_path/'history')
    assert store.turns(a['chat_id'])[0]['status']=='running' # ordinary open must not interrupt a live writer
    store.close();store=ChatStore(tmp_path/'history',recover=True)
    assert store.turns(a['chat_id'])[0]['status']=='interrupted'
    newer=uid()
    with pytest.raises(ValueError,match='explicitly'):store.begin(a['chat_id'],uid(),newer,'question')
    store.attach(a['chat_id'],newer)
    assert store.events(a['chat_id'])[-1]['kind']=='session_boundary'
    store.delete(a['chat_id']);assert store.list()==[b]
    store.close()


def stream(chunks,done=True):
    return ''.join('data: '+json.dumps(c)+'\n\n' for c in chunks)+('data: [DONE]\n\n' if done else '')


def chunk(delta,finish=None):return {'choices':[{'index':0,'delta':delta,'finish_reason':finish}]}


def test_native_stream_fragments_and_hidden_continuation():
    async def scenario():
        seen=[];visible=[]
        def handler(request):
            seen.append(json.loads(request.content))
            return httpx.Response(200,text=stream([
                chunk({'reasoning_content':'private reasoning'}),
                chunk({'content':'Looking'}),
                chunk({'tool_calls':[{'index':0,'id':'call_1','type':'function','function':{'name':'game_status','arguments':'{'}}]}),
                chunk({'tool_calls':[{'index':0,'function':{'arguments':'}'}}]},'tool_calls')]))
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter=DeepSeek('test-key',client=client)
            reply=await adapter.complete([{'role':'user','content':'hello'}],[],visible.append)
        assert visible==['Looking'];assert reply['reasoning_content']=='private reasoning'
        assert reply['tool_calls'][0]['function']['arguments']=='{}'
        assert seen[0]['model']=='deepseek-flash'
    run(scenario())


@pytest.mark.parametrize('body',[
    stream([chunk({'content':'partial'})],False),
    stream([chunk({'content':'partial'},'length')]),
    stream([{'choices':[42]}]),
    stream([chunk({'tool_calls':[None]})]),
    stream([chunk({'content':'a'},'stop'),chunk({'content':'b'})]),
    stream([chunk({'tool_calls':[{'index':0,'id':'x','function':{'name':'game_status','arguments':'{}'}}]},'stop')]),
])
def test_native_rejects_malformed_or_incomplete_stream(body):
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _:httpx.Response(200,text=body))) as client:
            with pytest.raises(ProviderError):await DeepSeek('key',client=client).complete([],[])
    run(scenario())


def test_http_failure_never_echoes_provider_error_body():
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _:httpx.Response(401,text='secret-key'))) as client:
            with pytest.raises(ProviderError) as caught:await DeepSeek('secret-key',client=client).complete([],[])
            assert 'secret-key' not in str(caught.value)
    run(scenario())


class MCP:
    def __init__(self,session):self.session=session;self.calls=[]
    async def list_tools(self):
        return SimpleNamespace(tools=[Tool(name=n,input_schema={'type':'object'},annotations=ToolAnnotations(read_only_hint=True)) for n in TOOLS])
    async def call_tool(self,name,args,**kwargs):
        self.calls.append((name,args))
        result={'session_id':self.session,'fresh':True,'live':True} if name=='game_status' else {'evidence':'bounded result'}
        return CallToolResult(content=[TextContent(type='text',text=json.dumps(result))],structured_content=result)


class Provider:
    def __init__(self,replies):self.replies=list(replies);self.messages=[];self.closed=False
    async def complete(self,messages,tools,on_text):
        self.messages.append(list(messages))
        reply=self.replies.pop(0)
        if isinstance(reply,BaseException):raise reply
        on_text(reply.get('content') or '')
        return reply
    async def close(self):self.closed=True


def answer(text):return {'role':'assistant','content':text,'reasoning_content':'hidden'}


def tool(name='search_guidance',arguments='{"query":"food"}'):
    return dict(answer('Checking'),tool_calls=[{'id':'call_1','type':'function','function':{'name':name,'arguments':arguments}}])


def test_loop_tools_followup_and_restart(tmp_path):
    async def scenario():
        session=uid();store=ChatStore(tmp_path);a=store.new(session,'A');b=store.new(session,'B')
        provider=Provider([tool(),answer('Cited answer'),answer('Follow up'),answer('Separate chat')])
        mcp=MCP(session);loop=Conversation(store,mcp,lambda _:provider)
        await loop.run(a['chat_id'],uid(),session,'Food?')
        assert ('search_guidance',{'query':'food'}) in mcp.calls
        await loop.run(a['chat_id'],uid(),session,'And storage?')
        assert any(m.get('reasoning_content')=='hidden' and m.get('content')=='Cited answer' for m in provider.messages[2])
        await loop.run(b['chat_id'],uid(),session,'Other question')
        assert not any(m.get('content')=='Cited answer' for m in provider.messages[3])
        raw=json.dumps(store.events(a['chat_id']))
        assert 'hidden' not in raw and 'reasoning_content' not in raw
        assert all('provider' in event['payload'] for event in store.events(a['chat_id']))
        restarted=Provider([answer('Restored')]);loop=Conversation(store,mcp,lambda _:restarted)
        await loop.run(a['chat_id'],uid(),session,'Continue')
        assert len([e for e in store.events(a['chat_id']) if e['kind']=='context_reset'])==2
        assert all(m['role']!='assistant' for m in restarted.messages[0])
        assert 'Cited answer' in restarted.messages[0][1]['content']
        store.close()
    run(scenario())


@pytest.mark.parametrize('case',['cancel','stale','duplicate','unknown-tool','bad-arguments'])
def test_loop_failure_and_retry_boundaries(tmp_path,case):
    async def scenario():
        session=uid();store=ChatStore(tmp_path);chat=store.new(session);cid=chat['chat_id'];turn=uid()
        provider=Provider([asyncio.CancelledError()] if case=='cancel' else [tool('execute_shell') if case=='unknown-tool' else tool(arguments='[]'),answer('Done')])
        mcp=MCP(uid() if case=='stale' else session);loop=Conversation(store,mcp,lambda _:provider)
        if case=='duplicate':
            store.begin(cid,turn,session,'one')
            with pytest.raises(ValueError,match='already exists'):await loop.run(cid,turn,session,'retry')
            assert provider.messages==[]
        elif case in {'cancel','stale'}:
            with pytest.raises(asyncio.CancelledError if case=='cancel' else ValueError):await loop.run(cid,turn,session,'Question')
            assert store.turns(cid)[0]['status']==('cancelled' if case=='cancel' else 'failed')
            assert cid not in loop.context and cid not in loop.running
        else:
            await loop.run(cid,turn,session,'Question')
            assert not any(n=='execute_shell' for n,_ in mcp.calls)
            tools=[e for e in store.events(cid) if e['kind']=='tool']
            assert 'error' in tools[-1]['payload']['result']
        store.close()
    run(scenario())


def test_coordinator_action_journal_and_local_history(tmp_path):
    from syx_chat_service import Coordinator,action,b64
    async def scenario():
        session=uid();store=ChatStore(tmp_path/'history');coordinator=Coordinator(store,MCP(session),tmp_path,'')
        rid=uid();request=action(('request_id='+rid+'\naction=new\nsession_id='+session+'\ntext='+b64('Test chat')+'\n').encode())
        await coordinator.dispatch(request);cid=coordinator.selected
        await coordinator.dispatch(request)
        assert len(store.list())==1
        await coordinator.dispatch({'request_id':uid(),'action':'select','session_id':session,'chat_id':cid})
        with pytest.raises(ValueError,match='key is missing'):
            await coordinator.dispatch({'request_id':uid(),'action':'send','session_id':session,'chat_id':cid,'text':'Hello'})
        assert not store.turns(cid)
        coordinator.write_ui();text=(tmp_path/'chat-ui.txt').read_text()
        assert 'chat_id='+cid in text and 'connected=false' in text
        # Durable admission survives coordinator restart; no second chat or paid retry.
        restarted=Coordinator(store,MCP(session),tmp_path,'')
        await restarted.dispatch(request);assert len(store.list())==1
        for raw in [b'action=new\n',b'request_id=x\n',b'x'*16385,('request_id='+uid()+'\naction=new\nsession_id='+session+'\naction=new\n').encode()]:
            with pytest.raises((ValueError,UnicodeError)):action(raw)
        store.close()
    run(scenario())


def test_real_stdio_mcp_chat_tool_discovery(tmp_path):
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    import os,sys
    async def scenario():
        params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],env={**os.environ,'SYX_STATE_DIR':str(tmp_path/'state')})
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as mcp:
                await mcp.initialize();listed=await mcp.list_tools()
                assert {t.name for t in listed.tools}==TOOLS
                assert all(t.annotations.read_only_hint is True for t in listed.tools)
                store=ChatStore(tmp_path/'history');session=uid();chat=store.new(session)
                provider=Provider([answer('Must not be sent')]);loop=Conversation(store,mcp,lambda _:provider)
                with pytest.raises(ValueError,match='fresh matching'):await loop.run(chat['chat_id'],uid(),session,'Question')
                assert not provider.messages
                store.close()
    run(scenario())


def test_configured_credential_redaction_across_stream_fragments(tmp_path):
    class FragmentProvider(Provider):
        async def complete(self,messages,tools,on_text):
            for part in ['value: secre','t-creden','tial done']:on_text(part)
            return answer('value: secret-credential done')
    async def scenario():
        session=uid();store=ChatStore(tmp_path,secrets=['secret-credential']);chat=store.new(session);visible=[]
        loop=Conversation(store,MCP(session),lambda _:FragmentProvider([]))
        result=await loop.run(chat['chat_id'],uid(),session,'Question',visible.append)
        assert ''.join(visible)=='value: [credential redacted] done'
        assert 'secret-credential' not in result
        assert 'secret-credential' not in json.dumps(store.events(chat['chat_id']))
        store.close()
    run(scenario())


def test_cleanup_failure_cannot_change_completed_turn(tmp_path):
    class CloseFailure(Provider):
        async def close(self):raise RuntimeError('connection cleanup')
    async def scenario():
        session=uid();store=ChatStore(tmp_path);chat=store.new(session);turn=uid()
        loop=Conversation(store,MCP(session),lambda _:CloseFailure([answer('Completed')]))
        assert await loop.run(chat['chat_id'],turn,session,'Question')=='Completed'
        assert store.turns(chat['chat_id'])[0]['status']=='completed'
        with pytest.raises(ValueError,match='game session'):
            store.append(chat['chat_id'],turn,uid(),'assistant',{'text':'Wrong provenance'})
        store.close()
    run(scenario())


def test_literal_credential_file_no_execution_or_interpolation(tmp_path):
    from syx_chat_service import read_key_file
    path=tmp_path/'credentials'
    path.write_text('# local credentials\nexport DEEPSEEK_API_KEY = "sample-value" # comment\n')
    assert read_key_file(path)=='sample-value'
    path.write_text('DEEPSEEK_API_KEY=literal$(touch${IFS}marker)\n')
    assert read_key_file(path)=='literal$(touch${IFS}marker)'
    assert not (tmp_path/'marker').exists()
    for text in ['', 'DEEPSEEK_API_KEY=\n','DEEPSEEK_API_KEY="two words"\n','DEEPSEEK_API_KEY=a\nDEEPSEEK_API_KEY=b\n']:
        path.write_text(text)
        with pytest.raises(ValueError):read_key_file(path)
    link=tmp_path/'linked';link.symlink_to(path)
    with pytest.raises(OSError):read_key_file(link)


def test_export_rename_delete_and_evidence_controls(tmp_path):
    from syx_chat_service import Coordinator,unb64
    async def scenario():
        session=uid();store=ChatStore(tmp_path/'history',secrets=['private-key']);chat=store.new(session);cid=chat['chat_id'];turn=uid()
        store.begin(cid,turn,session,'Question')
        store.append(cid,turn,session,'tool',{'name':'query_game_state','arguments':{},'result':{'structuredContent':{'state':{'session_id':session,'tick':7},'detail':'expanded-value'}}})
        store.append(cid,turn,session,'assistant',{'text':'Answer','reasoning_content':'hidden-value'})
        store.finish(cid,turn,'completed')
        coordinator=Coordinator(store,MCP(session),tmp_path,'')
        async def dispatch(name,**extra):
            await coordinator.dispatch(dict(request_id=uid(),action=name,session_id=session,chat_id=cid,**extra))
        await dispatch('rename',text='Renamed private-key')
        assert store.chat(cid)['title']=='Renamed [credential redacted]'
        await dispatch('select');coordinator.write_ui()
        def lines():return '\n'.join(unb64(line[5:]) for line in (tmp_path/'chat-ui.txt').read_text().splitlines() if line.startswith('line='))
        assert 'expanded-value' not in lines() and '"tick": 7' in lines()
        await dispatch('evidence');coordinator.write_ui();assert 'expanded-value' in lines()
        await dispatch('export')
        path=tmp_path/'history/exports'/f'{cid}.json'
        data=json.loads(path.read_text());assert data['chat']['chat_id']==cid
        assert 'private-key' not in path.read_text() and 'hidden-value' not in path.read_text()
        assert stat.S_IMODE(path.stat().st_mode)==0o600
        await dispatch('delete');assert store.list()==[] and path.exists()
        assert coordinator.selected is None
        store.close()
    run(scenario())


def test_claude_worker_environment_blocks_provider_fallback(monkeypatch):
    from syx_claude import worker_environment
    for name in ['DEEPSEEK_API_KEY','OPENAI_API_KEY','ANTHROPIC_API_KEY','ANTHROPIC_BASE_URL','CLAUDE_CODE_USE_BEDROCK','CLAUDE_CODE_OAUTH_TOKEN']:
        monkeypatch.setenv(name,'must-not-inherit')
    env=worker_environment()
    assert all(env.get(name)!='must-not-inherit' for name in ['DEEPSEEK_API_KEY','OPENAI_API_KEY','ANTHROPIC_API_KEY','ANTHROPIC_BASE_URL','CLAUDE_CODE_USE_BEDROCK','CLAUDE_CODE_OAUTH_TOKEN'])


@pytest.mark.parametrize("route",["subscription","api"])
def test_claude_sdk_bridge_preserves_ids_history_and_read_only_boundary(tmp_path,monkeypatch,route):
    from syx_claude import ClaudeConversation
    import syx_claude
    class Output:
        def __init__(self,events):self.events=list(events)
        async def readline(self):return (json.dumps(self.events.pop(0))+'\n').encode() if self.events else b''
    class Input:
        def __init__(self):self.lines=[]
        def write(self,raw):self.lines.append(json.loads(raw))
        async def drain(self):pass
    class Process:
        pid=123456789
        def __init__(self,events):self.stdout=Output(events);self.stdin=Input()
        async def wait(self):return 0
    async def scenario():
        session=uid();store=ChatStore(tmp_path);chat=store.new(session,provider='claude',model='haiku',route=route);turn=uid()
        bridge=uid();proc=Process([
            {'type':'tool','request_id':bridge,'name':'query_game_state','arguments':{'domain':'population'}},
            {'type':'phase','text':'Checking','tool_calls':[{'id':'sdk_call_1','name':'mcp__syx__query_game_state','arguments':{'domain':'population'}}],'resolved_model':'test-model'},
            {'type':'text','text':'Answer'}, {'type':'result','success':True,'text':'Answer'}])
        async def spawn(*args,**kwargs):return proc
        monkeypatch.setattr(syx_claude.asyncio,'create_subprocess_exec',spawn)
        monkeypatch.setattr(syx_claude.os,'killpg',lambda *_:None)
        loop=ClaudeConversation(store,MCP(session),None,api_key="test-api-key" if route=="api" else "");visible=[]
        assert await loop.run(chat['chat_id'],turn,session,'Question',visible.append)=='Answer'
        assert visible==['Answer'] and store.turns(chat['chat_id'])[0]['status']=='completed'
        assert proc.stdin.lines[1]['request_id']==bridge
        events=store.events(chat['chat_id'])
        assert any(e['payload'].get('bridge_request_id')==bridge for e in events)
        assert any(e['payload'].get('tool_calls',[{}])[0].get('id')=='sdk_call_1' for e in events if e['kind']=='assistant' and e['payload'].get('tool_calls'))
        assert all(e['payload']['route']==route for e in events)
        assert proc.stdin.lines[0]['route']==route
        store.close()
    run(scenario())


def test_claude_api_missing_key_never_uses_subscription(tmp_path):
    from syx_chat_service import Coordinator
    async def scenario():
        session=uid();store=ChatStore(tmp_path/'history');coordinator=Coordinator(store,MCP(session),tmp_path,'')
        await coordinator.dispatch(dict(request_id=uid(),action='new',session_id=session,provider='claude',route='api',model='haiku',text='API chat'))
        cid=coordinator.selected
        with pytest.raises(ValueError,match='subscription fallback is disabled'):
            await coordinator.dispatch(dict(request_id=uid(),action='send',session_id=session,chat_id=cid,text='Question'))
        assert not store.turns(cid) and not coordinator.tasks
        assert store.chat(cid)['route']=='api'
        store.close()
    run(scenario())


def test_simple_player_interface_defaults_to_pro_and_omits_debug_events(tmp_path):
    from syx_chat_service import Coordinator,unb64
    async def scenario():
        session=uid();store=ChatStore(tmp_path/'history')
        old=store.new(session,'Old flash')
        coordinator=Coordinator(store,MCP(session),tmp_path,'',simple=True)
        await coordinator.dispatch({'request_id':uid(),'action':'new','session_id':session})
        cid=coordinator.selected
        assert store.chat(cid)['model']=='deepseek-v4-pro'
        turn=uid();store.begin(cid,turn,session,'What needs attention?')
        store.append(cid,turn,session,'tool',{'name':'query_game_state','arguments':{'private_debug':'never display'},'result':{'rows':[42]}})
        store.append(cid,turn,session,'assistant',{'text':'Your answer.','tool_calls':[{'id':'internal'}]})
        coordinator.write_ui()
        raw=(tmp_path/'chat-ui.txt').read_text()
        visible=[unb64(line[5:]) for line in raw.splitlines() if line.startswith('line=')]
        assert visible==['You: What needs attention?','Assistant: Your answer.']
        assert 'chat='+old['chat_id'] not in raw
        assert 'private_debug' not in str(visible) and 'internal' not in str(visible)
        with pytest.raises(ValueError,match='DeepSeek Pro'):
            await coordinator.dispatch({'request_id':uid(),'action':'new','session_id':session,'model':'deepseek-flash'})
        assert len(store.list())==2 and not coordinator.tasks
        assert 'raw JSON' in coordinator.loop.instructions
        store.close()
    run(scenario())


def test_explicit_pro_is_sent_without_flash_fallback():
    async def scenario():
        sent=[]
        def handler(request):
            sent.append(json.loads(request.content))
            return httpx.Response(200,text=stream([chunk({'content':'Hello'},'stop')]))
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            reply=await DeepSeek('test-key','deepseek-v4-pro',client).complete([],[])
        assert reply['content']=='Hello' and sent[0]['model']=='deepseek-v4-pro'
    run(scenario())
