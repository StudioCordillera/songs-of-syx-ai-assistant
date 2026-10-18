"""Local chat coordinator. File IPC only; no listening network port or game access.

The player launcher defaults to a simplified DeepSeek Pro interface. Advanced
developer mode retains the experimental additional provider controls.
"""
import argparse
import asyncio
import base64
import contextlib
import fcntl
import json
import os
from pathlib import Path
import stat
import shlex
import sys
import time
from uuid import UUID

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from syx_chat import Conversation
from syx_chat_store import ChatStore, identity
from syx_deepseek import DeepSeek


def read_key_file(path,name="DEEPSEEK_API_KEY"):
    """Read one literal dotenv entry, without shell execution or interpolation."""
    fd=os.open(Path(path).expanduser(),os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as file:
        if not stat.S_ISREG(os.fstat(file.fileno()).st_mode):raise ValueError('Credential file must be regular')
        raw=file.read(16385)
    if len(raw)>16384:raise ValueError('Credential file exceeds 16 KiB')
    found=[]
    for line in raw.decode('utf-8-sig').splitlines():
        line=line.strip()
        if line.startswith('export '):line=line[7:].lstrip()
        entry,sep,value=line.partition('=')
        if sep and entry.strip()==name:
            parts=shlex.split(value,comments=True,posix=True)
            if len(parts)!=1 or not parts[0] or any(c.isspace() for c in parts[0]):
                raise ValueError('Invalid DeepSeek credential entry')
            found.append(parts[0])
    if len(found)!=1:raise ValueError('Exactly one '+name+' entry is required')
    return found[0]


def b64(text):return base64.b64encode(text.encode()).decode('ascii')


def unb64(text):
    return base64.b64decode(text,validate=True).decode('utf-8')


def action(raw):
    if len(raw)>16384:raise ValueError('Chat action exceeds 16 KiB')
    fields={}
    for line in raw.decode('ascii').splitlines():
        key,sep,value=line.partition('=')
        if not sep or key in fields or key not in {'request_id','action','session_id','chat_id','text','provider','route','model'}:raise ValueError('Invalid chat action')
        fields[key]=value
    if not {'request_id','action','session_id'}<=fields.keys():raise ValueError('Incomplete chat action')
    identity(fields['request_id']);identity(fields['session_id'])
    if 'chat_id' in fields:identity(fields['chat_id'])
    if fields['action'] not in {'new','select','send','stop','attach','evidence','rename','export','delete'}:raise ValueError('Unknown chat action')
    if fields['action']!='new' and 'chat_id' not in fields:raise ValueError('Chat selection required')
    if 'text' in fields:fields['text']=unb64(fields['text'])
    return fields


class Coordinator:
    def __init__(self,store,mcp,state_dir,api_key,claude_api_key="",simple=False):
        self.simple=simple
        self.store=store;self.mcp=mcp;self.directory=Path(state_dir);self.key=api_key;self.claude_api_key=claude_api_key
        self.loop=Conversation(store,mcp,lambda chat:DeepSeek(api_key,chat['model']))
        if simple:self.loop.instructions+='\nPlayer interface: answer in plain language. Keep raw JSON, tool calls, session IDs, snapshot IDs, ticks and JSON pointers in the local evidence log rather than the player-facing text. Cite human-readable guide URLs or installed source names when supporting mechanics. Do not narrate internal protocols.'
        from syx_claude import ClaudeConversation
        self.claude_loop=ClaudeConversation(store,mcp,None,api_key=claude_api_key)
        self.tasks={};self.selected=None;self.ack='';self.notice='DeepSeek API configured' if api_key else 'DeepSeek API key missing; set DEEPSEEK_API_KEY before starting the coordinator'
        self.partial={};self.last_write=0;self.expanded=set();self.validated=set()
        with store.db:
            store.db.execute('CREATE TABLE IF NOT EXISTS actions(request_id TEXT PRIMARY KEY, at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')

    async def dispatch(self,request):
        rid=request['request_id']
        if self.store.db.execute('SELECT 1 FROM actions WHERE request_id=?',(rid,)).fetchone():
            self.ack=rid;return
        # Persist admission before handling an action. An interrupted action is never auto-replayed.
        with self.store.db:self.store.db.execute('INSERT INTO actions(request_id) VALUES(?)',(rid,))
        self.ack=rid
        name=request['action'];session=request['session_id'];cid=request.get('chat_id')
        if self.simple:
            if name=='new':
                choice=(request.get('provider','deepseek'),request.get('route','api'),request.get('model','deepseek-v4-pro'))
                if choice!=('deepseek','api','deepseek-v4-pro'):raise ValueError('This user-test build uses DeepSeek Pro')
            elif name=='evidence':raise ValueError('Developer evidence controls are disabled in this user-test build')
            elif self.store.chat(cid)['model']!='deepseek-v4-pro' or self.store.chat(cid)['provider']!='deepseek':
                raise ValueError('Start a new DeepSeek Pro chat in this user-test build')
        if name=='new':
            self.selected=self.store.new(session,request.get('text') or 'New chat',request.get('provider','deepseek'),request.get('model','deepseek-v4-pro' if self.simple else 'deepseek-flash'),request.get('route','api'))['chat_id'];self.notice='Chat created';return
        selected_chat=self.store.chat(cid);self.selected=cid
        if name=='evidence':
            if cid in self.expanded:self.expanded.remove(cid)
            else:self.expanded.add(cid)
            self.notice='Tool evidence expanded' if cid in self.expanded else 'Tool evidence collapsed';return
        if name=='rename':
            self.store.rename(cid,request.get('text',''));self.notice='Chat renamed';return
        if name=='export':
            path=self.store.export(cid);self.notice='Chat exported locally: '+str(path);return
        if name=='delete':
            if cid in self.tasks and not self.tasks[cid].done():raise ValueError('Stop the reply before deleting its chat')
            self.store.delete(cid);self.loop.context.pop(cid,None);self.expanded.discard(cid)
            self.selected=None;self.notice='Chat deleted from history; previously exported files are retained';return
        if name=='select':self.notice='History loaded; continuing in a different runtime requires Attach';return
        if name=='attach':
            if cid in self.tasks and not self.tasks[cid].done():raise ValueError('Stop the running reply before attaching a new game session')
            self.store.attach(cid,session);self.loop.context.pop(cid,None);self.notice='Chat attached explicitly to this game session';return
        if name=='stop':
            task=self.tasks.get(cid)
            if task and not task.done():task.cancel();self.notice='Stopping reply'
            return
        if selected_chat['attached_session']!=session:raise ValueError('This chat belongs to another runtime session; explicitly Attach to this game first')
        if (selected_chat['provider'],selected_chat['route'])==('claude','api') and not self.claude_api_key:raise ValueError('Claude API key is missing; subscription fallback is disabled')
        if selected_chat['provider']=='deepseek' and not self.key:raise ValueError('DeepSeek API key is missing; no request sent')
        if cid in self.tasks and not self.tasks[cid].done():raise ValueError('A reply is already running')
        if self.simple and selected_chat['title']=='New chat':
            self.store.rename(cid,request.get('text','New chat')[:60] or 'New chat')
        # A duplicate action ID is also the durable turn ID. Both journals prevent resubmission.
        self.partial[cid]=''
        def emit(text):self.partial[cid]+=text
        async def reply():
            try:
                engine=self.loop if selected_chat['provider']=='deepseek' else self.claude_loop
                await engine.run(cid,rid,session,request.get('text',''),emit)
                self.notice='Reply completed';self.validated.add((selected_chat['provider'],selected_chat['route']))
            except asyncio.CancelledError:self.notice='Reply cancelled; partial output is retained'
            except Exception:self.notice='Reply failed; inspect the transcript. No provider or billing fallback was attempted.'
            finally:self.partial.pop(cid,None)
        self.tasks[cid]=asyncio.create_task(reply());self.notice='Generating with DeepSeek API'

    def write_ui(self):
        lines=['protocol=1','updated_at='+str(time.time()),'request_id='+self.ack,
            'notice='+b64(self.store.clean(self.notice)), 'connected='+str(bool(self.key)).lower(),
            'connection_status='+b64('DeepSeek API verified this run' if ('deepseek','api') in self.validated else 'DeepSeek API key loaded; not yet verified' if self.key else 'DeepSeek API key missing')]
        for chat in self.store.list():
            if not self.simple or (chat['provider'],chat['route'],chat['model'])==('deepseek','api','deepseek-v4-pro'):
                lines.append('chat='+chat['chat_id']+'|'+b64(chat['title']))
        if self.selected:
            chat=self.store.chat(self.selected)
            if chat['provider']=='claude':
                lines=[line for line in lines if not line.startswith('connection_status=')]
                route=chat['route']
                label='Claude '+route+' verified this run' if ('claude',route) in self.validated else 'Claude subscription via official client; not yet verified' if route=='subscription' else 'Claude API key loaded; not yet verified' if self.claude_api_key else 'Claude API key missing; no plan fallback'
                lines.append('connection_status='+b64(label))
            lines+=['provider='+chat['provider'],'model='+chat['model'],'route='+chat['route']]
            lines+=['chat_id='+self.selected,'session_id='+chat['attached_session'],
                'running='+str(self.selected in self.tasks and not self.tasks[self.selected].done()).lower()]
            # Latest 100 events; omitted history is explicit. Full history stays in SQLite.
            rows=self.store.db.execute('SELECT sequence FROM events WHERE chat_id=? ORDER BY sequence DESC LIMIT 100',(self.selected,)).fetchall()
            after=min((r[0] for r in rows),default=1)-1
            if self.store.db.execute('SELECT 1 FROM events WHERE chat_id=? AND sequence<=? LIMIT 1',(self.selected,after)).fetchone():
                lines.append('line='+b64('[Earlier events retained locally; this preview shows the latest 100 events.]'))
            for event in self.store.events(self.selected,after=after,limit=100):
                payload=event['payload'];kind=event['kind']
                if self.simple:
                    if kind in {'user','assistant'}:
                        text=payload.get('text','')
                        if not text:continue
                        text=('You: ' if kind=='user' else 'Assistant: ')+text
                    elif kind in {'turn_error','turn_cancelled'}:text='Reply interrupted. Please try again or start a new chat.'
                    elif kind=='session_boundary':text='Conversation connected to this game.'
                    else:continue
                    lines.append('line='+b64(text));continue
                if kind=='tool':
                    if self.selected in self.expanded:text='Tool evidence: '+json.dumps(payload,ensure_ascii=False)
                    else:
                        result=payload.get('result',{})
                        structured=Conversation._status(result)
                        provenance=structured.get('state',structured)
                        if not isinstance(provenance,dict):provenance={}
                        metadata={key:provenance[key] for key in ('session_id','snapshot_id','request_id','capture_id','tick','captured_at','available','error') if key in provenance}
                        text='Tool: '+payload.get('name','')+' '+json.dumps(payload.get('arguments',{}),ensure_ascii=False)[:1000]+' | '+json.dumps(metadata)+' [Evidence button expands bounded results]'
                        if result.get('isError') or result.get('error'):text+=' [Tool error; expand for details]'
                else:text=kind+': '+str(payload.get('text',payload.get('message',json.dumps(payload,ensure_ascii=False))))
                text=event['at']+' ['+event['game_session']+'] '+text
                if len(text)>16000:text=text[:15900]+' [Preview truncated; full bounded event retained locally.]'
                lines.append('line='+b64(text))
            if self.selected in self.partial:lines.append('line='+b64(('Assistant: ' if self.simple else 'Streaming: ')+self.store.clean(self.partial[self.selected])))
        # Drop oldest preview lines to fit IPC budget; never silently truncate a paid request.
        while len(('\n'.join(lines)+'\n').encode())>240000:
            indices=[i for i,line in enumerate(lines) if line.startswith('line=')]
            if not indices:raise ValueError('Chat UI metadata exceeds bounds')
            lines.pop(indices[0])
            if not any(line.startswith('omitted=') for line in lines):lines.insert(1,'omitted=true')
        temporary=self.directory/'chat-ui.tmp'
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w',encoding='ascii') as file:file.write('\n'.join(lines)+'\n')
        os.replace(temporary,self.directory/'chat-ui.txt')

    async def serve(self):
        last=None
        try:
            while True:
                path=self.directory/'chat-action.txt'
                try:
                    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
                    with os.fdopen(fd,'rb') as file:
                        if not stat.S_ISREG(os.fstat(file.fileno()).st_mode):raise ValueError('Chat action must be a regular file')
                        raw=file.read(16385)
                    if raw!=last:
                        last=raw
                        try:await self.dispatch(action(raw))
                        except Exception as error:
                            self.notice=self.store.clean(str(error)) if isinstance(error,ValueError) else 'Chat action rejected; check session, selection, message bounds and connection'
                except FileNotFoundError:pass
                self.write_ui()
                await asyncio.sleep(0.1)
        finally:
            for task in self.tasks.values():
                if not task.done():task.cancel()
            await asyncio.gather(*self.tasks.values(),return_exceptions=True)
            self.notice='Coordinator stopped';self.key='';self.write_ui()


async def serve(args):
    directory=Path(args.state_dir).expanduser()
    if directory.is_symlink():raise ValueError('State directory cannot be a symlink')
    directory.mkdir(parents=True,exist_ok=True,mode=0o700);directory.chmod(0o700)
    lock_path=Path(args.history_dir).expanduser()
    if lock_path.is_symlink():raise ValueError('History directory cannot be a symlink')
    lock_path.mkdir(parents=True,exist_ok=True,mode=0o700);lock_path.chmod(0o700)
    fd=os.open(lock_path/'coordinator.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('A coordinator already owns this history directory')
        from syx_knowledge import install_seed
        install_seed(directory) # Merge reviewed starter summaries, preserving existing records and retrieval dates.
        key=read_key_file(args.env_file) if args.env_file else os.environ.get('DEEPSEEK_API_KEY','')
        claude_key=read_key_file(args.claude_env_file,'ANTHROPIC_API_KEY') if args.claude_env_file else os.environ.get('ANTHROPIC_API_KEY','')
        store=ChatStore(lock_path,secrets=[key,claude_key],recover=True)
        try:
            # Do not give a child MCP process the provider credential.
            env={k:v for k,v in os.environ.items() if k not in {'DEEPSEEK_API_KEY','OPENAI_API_KEY','ANTHROPIC_API_KEY'}}
            env['SYX_STATE_DIR']=str(directory.absolute())
            params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],env=env)
            async with stdio_client(params) as (read,write):
                async with ClientSession(read,write) as mcp:
                    await mcp.initialize()
                    await Coordinator(store,mcp,directory,key,claude_key,simple=not args.advanced).serve()
        finally:store.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir',default=os.environ.get('SYX_STATE_DIR',str(Path.home()/'.local/share/syx-assistant')))
    parser.add_argument('--history-dir',default=str(Path.home()/'.local/share/syx-assistant-chat'))
    parser.add_argument('--env-file',help='Read DEEPSEEK_API_KEY from a local literal dotenv file; never executes shell content')
    parser.add_argument('--advanced',action='store_true',help='Developer UI output and additional providers; not used by the user-test launcher')
    parser.add_argument('--claude-env-file',help='Read ANTHROPIC_API_KEY from a local literal dotenv file for explicit Claude API chats')
    args=parser.parse_args()
    try:asyncio.run(serve(args))
    except KeyboardInterrupt:pass


if __name__=='__main__':main()
