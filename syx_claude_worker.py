"""Private JSONL worker for the official Claude Agent SDK; no game-process access.

Only visible text and read-only tool protocol events leave this process. The SDK
owns subscription authentication and provider-internal continuation within a turn.
"""
import asyncio
import json
import os
import shutil
import sys
from uuid import uuid4


def send(value):
    raw=json.dumps(value,ensure_ascii=False,allow_nan=False)
    if len(raw.encode())>1024*1024:raise ValueError('Worker event too large')
    print(raw,flush=True)


async def read():
    raw=await asyncio.to_thread(sys.stdin.buffer.readline,2*1024*1024+1)
    if not raw or len(raw)>2*1024*1024:raise ValueError('Invalid worker input')
    return json.loads(raw)


async def main():
    from claude_agent_sdk import ClaudeAgentOptions,query,ResultMessage,AssistantMessage,StreamEvent,SystemMessage
    from claude_agent_sdk import SdkMcpTool,create_sdk_mcp_server,TextBlock,ToolUseBlock
    from mcp.types import ToolAnnotations
    initial=await read();cli=shutil.which('claude')
    if not cli:send({'type':'error','code':'official_client_missing'});return
    route=initial.get('route','subscription')
    if route=='api':
        key=os.environ.pop('SYX_CLAUDE_API_KEY','')
        if not key:send({'type':'error','code':'api_key_required'});return
        os.environ['ANTHROPIC_API_KEY']=key
    elif route!='subscription':send({'type':'error','code':'unsupported_route'});return
    process=await asyncio.create_subprocess_exec(cli,'auth','status','--json',stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL)
    stdout,_=await process.communicate()
    status=json.loads(stdout)
    if process.returncode or not status.get('loggedIn') or status.get('authMethod')!=('claude.ai' if route=='subscription' else 'api_key'):
        send({'type':'error','code':'selected_authentication_route_unavailable'});return
    lock=asyncio.Lock()
    def tool(spec):
        async def handle(arguments):
            async with lock:
                request_id=str(uuid4())
                send({'type':'tool','request_id':request_id,'name':spec['name'],'arguments':arguments})
                response=await read()
                if response.get('request_id')!=request_id:raise ValueError('Tool response identity mismatch')
                result=response['result']
                return {'content':[{'type':'text','text':json.dumps(result,ensure_ascii=False,allow_nan=False)}],
                    'is_error':bool(result.get('isError') or result.get('error'))}
        return SdkMcpTool(spec['name'],spec['description'],spec['parameters'],handle,
            ToolAnnotations(read_only_hint=True,destructive_hint=False,open_world_hint=False))
    tools=[tool(spec) for spec in initial['tools']]
    allowed=['mcp__syx__'+spec['name'] for spec in initial['tools']]
    options=ClaudeAgentOptions(model=initial['model'],tools=[],allowed_tools=allowed,strict_mcp_config=True,
        mcp_servers={'syx':create_sdk_mcp_server('syx',tools=tools)},system_prompt=initial['instructions'],
        setting_sources=[],skills=[],permission_mode='dontAsk',max_turns=8,max_budget_usd=1.0,
        include_partial_messages=True,extra_args={'no-session-persistence':None,'disable-slash-commands':None},
        cli_path=cli,stderr=lambda _:None,thinking={'type':'disabled'})
    async for message in query(prompt=initial['prompt'],options=options):
        if isinstance(message,SystemMessage) and message.subtype=='init':
            if set(message.data.get('tools',[]))-set(allowed):
                send({'type':'error','code':'unexpected_tool_set'});return
        elif isinstance(message,StreamEvent):
            event=message.event;delta=event.get('delta',{})
            if event.get('type')=='content_block_delta' and delta.get('type')=='text_delta':
                send({'type':'text','text':delta.get('text','')})
        elif isinstance(message,AssistantMessage):
            text=''.join(block.text for block in message.content if isinstance(block,TextBlock))
            calls=[{'id':block.id,'name':block.name,'arguments':block.input} for block in message.content if isinstance(block,ToolUseBlock)]
            send({'type':'phase','text':text,'tool_calls':calls,'resolved_model':message.model})
        elif isinstance(message,ResultMessage):
            valid=not message.is_error and message.subtype=='success' and getattr(message,'terminal_reason',None)=='completed'
            send({'type':'result','success':valid,'text':message.result or ''})


if __name__=='__main__':
    try:asyncio.run(main())
    except BaseException:send({'type':'error','code':'sdk_failed'})
