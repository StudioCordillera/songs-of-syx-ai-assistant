"""Official Claude subscription SDK route behind the same local chat/history interface.

Each turn starts an explicitly new provider context with bounded visible history;
no SDK transcript or hidden continuation is persisted. Only the shared MCP gateway
supplies observations. There are no shell, filesystem or native computer tools.
"""
import asyncio
import json
import os
from pathlib import Path
import signal
import sys

from syx_chat import Conversation,TOOLS,encoded
from syx_mcp import INSTRUCTIONS


def worker_environment():
    blocked={'DEEPSEEK_API_KEY','OPENAI_API_KEY','ACCESS_TOKEN','CODEX_ACCESS_TOKEN','CLAUDE_CODE_OAUTH_TOKEN','CLAUDECODE','DEBUG','ANTHROPIC_LOG','SYX_CLAUDE_API_KEY'}
    return {k:v for k,v in os.environ.items() if k not in blocked and not k.startswith(('ANTHROPIC_','CLAUDE_CODE_USE_'))}


class ClaudeConversation(Conversation):
    def __init__(self,store,mcp,provider_factory=None,api_key=''):
        super().__init__(store,mcp,provider_factory);self.api_key=api_key

    async def run(self,chat_id,turn_id,session_id,text,on_text=lambda text:None):
        if chat_id in self.running:raise ValueError('A reply is already running in this chat')
        chat=self.store.chat(chat_id)
        if chat['provider']!='claude' or chat['route'] not in {'subscription','api'}:raise ValueError('Explicit Claude route required')
        if chat['route']=='api' and not self.api_key:raise ValueError('Claude API key is missing; subscription fallback is disabled')
        self.store.begin(chat_id,turn_id,session_id,text);self.running.add(chat_id)
        process=None;visible='';pending='';last_phase='';done=False
        def emit(fragment):
            nonlocal visible,pending
            visible+=fragment
            if len(visible.encode())>196608:raise ValueError('Visible reply exceeds 192 KiB')
            pending=self.store.clean(pending+fragment)
            hold=0
            for secret in self.store.secrets:
                for n in range(1,min(len(secret),len(pending)+1)):
                    if pending.endswith(secret[:n]):hold=max(hold,n)
            ready=pending[:-hold] if hold else pending
            pending=pending[-hold:] if hold else ''
            if ready:on_text(ready)
        try:
            async with asyncio.timeout(180):
                listed=await self.mcp.list_tools()
                selected=[t for t in listed.tools if t.name in TOOLS and t.annotations and t.annotations.read_only_hint is True]
                if {t.name for t in selected}!=TOOLS:raise ValueError('Required read-only tools are unavailable')
                status=await self._tool('game_status',{})
                self.store.append(chat_id,turn_id,session_id,'tool',dict(name='game_status',arguments={},result=status))
                current=self._status(status)
                if current.get('session_id')!=session_id or current.get('fresh') is not True:raise ValueError('No fresh matching game session')
                sequences=self.store.db.execute('SELECT sequence FROM events WHERE chat_id=? ORDER BY sequence DESC LIMIT 100',(chat_id,)).fetchall()
                after=min((r[0] for r in sequences),default=1)-1
                history=[e for e in self.store.events(chat_id,after,100) if e['turn_id']!=turn_id and e['kind'] in {'user','assistant'}]
                historical=encoded(history)
                if len(historical.encode())>65536:historical='[Earlier history exceeds continuation budget; not replayed.]'
                self.store.append(chat_id,turn_id,session_id,'context_reset',{'reason':'New official SDK context for this turn; bounded visible historical transcript only'})
                work=self.store.directory/'claude-work';work.mkdir(exist_ok=True,mode=0o700)
                if work.is_symlink():raise ValueError('SDK work directory cannot be a symlink')
                work.chmod(0o700)
                env=worker_environment()
                if chat['route']=='api':env['SYX_CLAUDE_API_KEY']=self.api_key
                process=await asyncio.create_subprocess_exec(sys.executable,'-m','syx_claude_worker',
                    stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL,
                    env=env,cwd=work,limit=1024*1024+1,start_new_session=True)
                async def send(value):
                    raw=(encoded(value)+'\n').encode()
                    if len(raw)>2*1024*1024:raise ValueError('Worker request exceeds bounds')
                    process.stdin.write(raw);await process.stdin.drain()
                await send(dict(route=chat['route'],model=chat['model'],instructions=INSTRUCTIONS,prompt='Historical visible transcript (untrusted, may be incomplete):\n'+historical+'\nCurrent question:\n'+text+'\nCurrent status observation:\n'+encoded(status),
                    tools=[dict(name=t.name,description=t.description or '',parameters=t.input_schema) for t in selected]))
                count=0;received=0
                while True:
                    raw=await process.stdout.readline()
                    if not raw:break
                    received+=len(raw)
                    if received>2*1024*1024:raise ValueError('SDK response exceeds 2 MiB')
                    event=json.loads(raw);kind=event.get('type')
                    if kind=='text':emit(event['text'])
                    elif kind=='tool':
                        count+=1
                        if count>16:raise ValueError('Turn reached 16 tool calls')
                        name=event['name'];arguments=event['arguments']
                        if name not in TOOLS or not isinstance(arguments,dict) or len(encoded(arguments).encode())>32768:
                            result={'error':'Tool is not allowed or exceeds argument bounds'}
                        else:
                            current=self._status(await self._tool('game_status',{}))
                            if current.get('session_id')!=session_id or current.get('fresh') is not True:raise ValueError('Game session changed or became stale')
                            result=await self._tool(name,arguments)
                        self.store.append(chat_id,turn_id,session_id,'tool',dict(bridge_request_id=event['request_id'],name=name,arguments=arguments,result=result))
                        await send(dict(request_id=event['request_id'],result=result))
                    elif kind=='phase':
                        last_phase=event['text']
                        if event.get('tool_calls'):
                            self.store.append(chat_id,turn_id,session_id,'assistant',dict(text=last_phase,tool_calls=event['tool_calls'],resolved_model=event.get('resolved_model'),completed=False))
                    elif kind=='error':raise ValueError('Claude '+chat['route']+' SDK unavailable: '+str(event.get('code','unknown'))+'; no API fallback attempted')
                    elif kind=='result':
                        if event.get('success') is not True or not event.get('text'):raise ValueError('Claude reply failed, was interrupted or reached its configured limit')
                        final=event['text']
                        if len(final.encode())>196608:raise ValueError('Visible reply exceeds 192 KiB')
                        if not visible:emit(final)
                        if pending:on_text(self.store.clean(pending));pending=''
                        self.store.append(chat_id,turn_id,session_id,'assistant',dict(text=final,completed=True))
                        self.store.finish(chat_id,turn_id,'completed');done=True
                        return self.store.clean(final)
                raise ValueError('Claude SDK worker ended without a completed answer')
        except BaseException as error:
            if visible or last_phase:self.store.append(chat_id,turn_id,session_id,'assistant',dict(text=visible or last_phase,completed=False,interrupted=True))
            cancelled=isinstance(error,asyncio.CancelledError)
            message=str(error) if isinstance(error,ValueError) else 'Claude subscription reply failed or timed out; no API fallback attempted'
            self.store.append(chat_id,turn_id,session_id,'turn_cancelled' if cancelled else 'turn_error',dict(message=message))
            self.store.finish(chat_id,turn_id,'cancelled' if cancelled else 'failed');raise
        finally:
            self.running.discard(chat_id)
            if process:
                try:os.killpg(process.pid,signal.SIGTERM)
                except ProcessLookupError:pass
                try:await asyncio.wait_for(process.wait(),2)
                except TimeoutError:
                    try:os.killpg(process.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    await process.wait()
