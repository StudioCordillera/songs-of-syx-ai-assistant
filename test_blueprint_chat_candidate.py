"""Developer conversation extension: admission/lifecycle, no inference or game mutation."""
import asyncio,json,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from datetime import datetime,timezone
import pytest
from mcp.types import Tool,ToolAnnotations,CallToolResult,TextContent
from syx_chat import Conversation,TOOLS
from syx_chat_store import ChatStore
from dev.blueprint_chat_candidate import BlueprintConversation,EXTRA

ROOT=Path(__file__).resolve().parent

def uid():return str(uuid4())
def result(value):return CallToolResult(content=[TextContent(type='text',text=json.dumps(value))])
def tool(name,args):return {'role':'assistant','content':'','tool_calls':[{'id':uid(),'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]}
def final(text='Reference caveats retained'):return {'role':'assistant','content':text}
class Provider:
    def __init__(self,replies):self.replies=list(replies);self.closed=False;self.rounds=[]
    async def complete(self,messages,schemas,emit):
        self.rounds.append((list(messages),schemas));reply=self.replies.pop(0)
        if isinstance(reply,BaseException):raise reply
        emit(reply.get('content',''));return reply
    async def close(self):self.closed=True
class MCP:
    def __init__(self,session):self.session=session;self.bad=None;self.changed=False;self.calls=[];self.schemas=[]
    async def list_tools(self):
        names=set(TOOLS)|EXTRA
        tools=[Tool(name=n,input_schema={'type':'object'},annotations=ToolAnnotations(read_only_hint=True,idempotent_hint=True,destructive_hint=False,open_world_hint=False)) for n in sorted(names)]
        if self.bad=='missing':tools=[t for t in tools if t.name!='get_blueprint_example']
        if self.bad=='duplicate':tools.append(next(t for t in tools if t.name=='get_blueprint_example'))
        for t in tools:
            if t.name in EXTRA and self.bad in ('writable','changed'):t.annotations.read_only_hint=False
        return SimpleNamespace(tools=tools)
    async def call_tool(self,name,args,**kwargs):
        self.calls.append(name)
        if name=='game_status':return result({'session_id':self.session,'fresh':True,'live':True})
        return result({'scope':'developer_reference_catalog_no_live_state','construction_validated':False,'execution_supported':False})

@pytest.mark.parametrize('bad',['missing','duplicate','writable'])
def test_admission_refuses_before_provider_or_durable_turn(tmp_path,bad):
    async def scenario():
        store=ChatStore(tmp_path/'history');session=uid();chat=store.new(session);mcp=MCP(session);mcp.bad=bad;p=Provider([])
        loop=BlueprintConversation(store,mcp,lambda _:p)
        with pytest.raises(ValueError):await loop.run(chat['chat_id'],uid(),session,'Question')
        assert not p.rounds and store.turns(chat['chat_id'])==[]
        assert (await loop._tool('get_blueprint_example',{}))['error'].startswith('Reference tools not admitted')
        store.close()
    asyncio.run(scenario())

def test_extension_uses_existing_history_lifecycle_and_keeps_base_allowlist(tmp_path):
    async def scenario():
        before=TOOLS;store=ChatStore(tmp_path/'history');session=uid();chat=store.new(session);mcp=MCP(session)
        p=Provider([tool('get_blueprint_example',{'request':{'example_id':'warehouse-two-items-teaching-grid','game_version':'0.71.44'}}),final()])
        loop=BlueprintConversation(store,mcp,lambda _:p)
        assert await loop.run(chat['chat_id'],uid(),session,'Show teaching example')=='Reference caveats retained'
        assert p.closed and len(p.rounds)==2 and TOOLS==before and len(TOOLS)==19
        assert {x['function']['name'] for x in p.rounds[0][1]}==TOOLS|EXTRA
        assert mcp.calls==['game_status','game_status','get_blueprint_example']
        assert store.turns(chat['chat_id'])[0]['status']=='completed'
        assert any(e['kind']=='tool' and e['payload']['name']=='get_blueprint_example' for e in store.events(chat['chat_id']))
        assert loop._reference_schemas.get() is None
        assert (await loop._tool('execute_game',{}))['error']=='Tool is not allowed'
        store.close()
    asyncio.run(scenario())

@pytest.mark.parametrize('kind',['invalid','changed','cancel'])
def test_request_recheck_and_cancellation_never_expand_authority(tmp_path,kind):
    async def scenario():
        store=ChatStore(tmp_path/'history');session=uid();chat=store.new(session);mcp=MCP(session)
        p=Provider([final()]);loop=BlueprintConversation(store,mcp,lambda _:p)
        class Controlled(Provider):
            async def complete(self,messages,schemas,emit):
                if kind=='cancel':raise asyncio.CancelledError()
                if not self.rounds:
                    self.rounds.append((messages,schemas))
                    if kind=='changed':mcp.bad='changed'
                    return tool('get_blueprint_example',{'request':{'example_id':'warehouse-two-items-teaching-grid','game_version':'0.71.44'},**({'execute':True} if kind=='invalid' else {})})
                return final()
        p=Controlled([])
        if kind=='cancel':
            with pytest.raises(asyncio.CancelledError):await loop.run(chat['chat_id'],uid(),session,'Question')
        else:await loop.run(chat['chat_id'],uid(),session,'Question')
        assert 'get_blueprint_example' not in mcp.calls and p.closed and not loop.running
        assert loop._reference_schemas.get() is None
        store.close()
    asyncio.run(scenario())

def test_actual_stdio_reference_tools_in_unchanged_conversation_loop(tmp_path):
    async def scenario():
        from mcp import ClientSession,StdioServerParameters
        from mcp.client.stdio import stdio_client
        with tempfile.TemporaryDirectory(dir=ROOT/'runtime',prefix='blueprint-conversation-') as name:
            state=Path(name);snapshot=json.loads((ROOT/'snapshot.example.json').read_text());session=uid();snapshot['session_id']=session;snapshot['captured_at']=datetime.now(timezone.utc).isoformat()
            # Explicit synthetic demo context; no claim of a real current world.
            assert snapshot['demo'] is True;(state/'snapshot.json').write_text(json.dumps(snapshot))
            params=StdioServerParameters(command=sys.executable,args=['-m','dev.blueprint_mcp_candidate'],cwd=str(ROOT),env={'SYX_STATE_DIR':str(state)})
            async with stdio_client(params) as streams:
              async with ClientSession(*streams) as mcp:
                await mcp.initialize();store=ChatStore(tmp_path/'actual-history');chat=store.new(session)
                p=Provider([tool('search_blueprint_examples',{'request':{'query':'warehouse aisle','game_version':'0.71.44'}}),
                    tool('get_blueprint_example',{'request':{'example_id':'warehouse-two-items-teaching-grid','game_version':'0.71.44'}}),final()])
                loop=BlueprintConversation(store,mcp,lambda _:p)
                await loop.run(chat['chat_id'],uid(),session,'Use original reference example, not demo world facts')
                events=[e for e in store.events(chat['chat_id']) if e['kind']=='tool'];assert [e['payload']['name'] for e in events]==['game_status','search_blueprint_examples','get_blueprint_example']
                value=json.loads(events[-1]['payload']['result']['content'][0]['text'])
                assert value['geometry']['grid']==['.....','.RF..','E....','.RF..','.....']
                assert value['execution_supported'] is False and value['construction_validated'] is False
                assert p.closed and len(p.rounds)==3 and store.turns(chat['chat_id'])[0]['status']=='completed'
                store.close()
    asyncio.run(scenario())


def test_completed_turn_revokes_inherited_child_context(tmp_path):
    async def scenario():
        store=ChatStore(tmp_path/'history');session=uid();chat=store.new(session);mcp=MCP(session)
        release=asyncio.Event();jobs=[]
        class Background(Provider):
            async def complete(self,messages,schemas,emit):
                async def late():
                    await release.wait()
                    return await loop._tool('get_blueprint_example',{'request':{'example_id':'warehouse-two-items-teaching-grid','game_version':'0.71.44'}})
                jobs.append(asyncio.create_task(late()));return final()
        p=Background([]);loop=BlueprintConversation(store,mcp,lambda _:p)
        await loop.run(chat['chat_id'],uid(),session,'Question');release.set()
        assert (await jobs[0])['error'].startswith('Reference tools not admitted')
        assert mcp.calls==['game_status'];store.close()
    asyncio.run(scenario())


def test_concurrent_chats_keep_their_own_provider_grants_and_histories(tmp_path):
    async def scenario():
        store=ChatStore(tmp_path/'history');session=uid();a=store.new(session);b=store.new(session);mcp=MCP(session)
        gate=asyncio.Event();started=asyncio.Event()
        class Delayed(Provider):
            async def complete(self,messages,schemas,emit):
                started.set();await gate.wait();return await super().complete(messages,schemas,emit)
        one=Delayed([final('First')]);two=Provider([final('Second')])
        loop=BlueprintConversation(store,mcp,lambda chat:one if chat['chat_id']==a['chat_id'] else two)
        pending=asyncio.create_task(loop.run(a['chat_id'],uid(),session,'First question'));await started.wait()
        assert await loop.run(b['chat_id'],uid(),session,'Second question')=='Second'
        gate.set();assert await pending=='First'
        assert one.closed and two.closed and not loop.running and loop._reference_schemas.get() is None
        for p in [one,two]:assert {t['function']['name'] for t in p.rounds[0][1]}==TOOLS|EXTRA
        assert store.turns(a['chat_id'])[0]['status']==store.turns(b['chat_id'])[0]['status']=='completed';store.close()
    asyncio.run(scenario())
