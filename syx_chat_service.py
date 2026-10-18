"""Local chat coordinator. File IPC only; no listening network port or game access.

Development launcher: syx-chat. Production in-game account setup/packaging remains
pending. Only the native DeepSeek API route is implemented by this coordinator.
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
import sys
import time
from uuid import UUID

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from syx_chat import Conversation
from syx_chat_store import ChatStore, identity
from syx_deepseek import DeepSeek


def b64(text):return base64.b64encode(text.encode()).decode('ascii')


def unb64(text):
    return base64.b64decode(text,validate=True).decode('utf-8')


def action(raw):
    if len(raw)>16384:raise ValueError('Chat action exceeds 16 KiB')
    fields={}
    for line in raw.decode('ascii').splitlines():
        key,sep,value=line.partition('=')
        if not sep or key in fields or key not in {'request_id','action','session_id','chat_id','text'}:raise ValueError('Invalid chat action')
        fields[key]=value
    if not {'request_id','action','session_id'}<=fields.keys():raise ValueError('Incomplete chat action')
    identity(fields['request_id']);identity(fields['session_id'])
    if 'chat_id' in fields:identity(fields['chat_id'])
    if fields['action'] not in {'new','select','send','stop','attach'}:raise ValueError('Unknown chat action')
    if fields['action']!='new' and 'chat_id' not in fields:raise ValueError('Chat selection required')
    if 'text' in fields:fields['text']=unb64(fields['text'])
    return fields


class Coordinator:
    def __init__(self,store,mcp,state_dir,api_key):
        self.store=store;self.mcp=mcp;self.directory=Path(state_dir);self.key=api_key
        self.loop=Conversation(store,mcp,lambda chat:DeepSeek(api_key,chat['model']))
        self.tasks={};self.selected=None;self.ack='';self.notice='DeepSeek API configured' if api_key else 'DeepSeek API key missing; set DEEPSEEK_API_KEY before starting the coordinator'
        self.partial={};self.last_write=0
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
        if name=='new':
            self.selected=self.store.new(session,request.get('text') or 'New chat')['chat_id'];self.notice='Chat created';return
        self.store.chat(cid);self.selected=cid
        if name=='select':self.notice='History loaded; continuing in a different runtime requires Attach';return
        if name=='attach':
            if cid in self.tasks and not self.tasks[cid].done():raise ValueError('Stop the running reply before attaching a new game session')
            self.store.attach(cid,session);self.loop.context.pop(cid,None);self.notice='Chat attached explicitly to this game session';return
        if name=='stop':
            task=self.tasks.get(cid)
            if task and not task.done():task.cancel();self.notice='Stopping reply'
            return
        if not self.key:raise ValueError('DeepSeek API key is missing; no request sent')
        if cid in self.tasks and not self.tasks[cid].done():raise ValueError('A reply is already running')
        # A duplicate action ID is also the durable turn ID. Both journals prevent resubmission.
        self.partial[cid]=''
        def emit(text):self.partial[cid]+=text
        async def reply():
            try:
                await self.loop.run(cid,rid,session,request.get('text',''),emit)
                self.notice='Reply completed'
            except asyncio.CancelledError:self.notice='Reply cancelled; partial output is retained'
            except Exception:self.notice='Reply failed; inspect the transcript. No provider or billing fallback was attempted.'
            finally:self.partial.pop(cid,None)
        self.tasks[cid]=asyncio.create_task(reply());self.notice='Generating with DeepSeek API'

    def write_ui(self):
        lines=['protocol=1','updated_at='+str(time.time()),'request_id='+self.ack,
            'notice='+b64(self.store.clean(self.notice)), 'connected='+str(bool(self.key)).lower()]
        for chat in self.store.list():lines.append('chat='+chat['chat_id']+'|'+b64(chat['title']))
        if self.selected:
            chat=self.store.chat(self.selected)
            lines+=['chat_id='+self.selected,'session_id='+chat['attached_session'],
                'running='+str(self.selected in self.tasks and not self.tasks[self.selected].done()).lower()]
            # Latest 100 events; omitted history is explicit. Full history stays in SQLite.
            rows=self.store.db.execute('SELECT sequence FROM events WHERE chat_id=? ORDER BY sequence DESC LIMIT 100',(self.selected,)).fetchall()
            after=min((r[0] for r in rows),default=1)-1
            if self.store.db.execute('SELECT 1 FROM events WHERE chat_id=? AND sequence<=? LIMIT 1',(self.selected,after)).fetchone():
                lines.append('line='+b64('[Earlier events retained locally; this preview shows the latest 100 events.]'))
            for event in self.store.events(self.selected,after=after,limit=100):
                payload=event['payload'];kind=event['kind']
                if kind=='tool':text='Tool evidence: '+json.dumps(payload,ensure_ascii=False)
                else:text=kind+': '+str(payload.get('text',payload.get('message',json.dumps(payload,ensure_ascii=False))))
                text=event['at']+' ['+event['game_session']+'] '+text
                if len(text)>16000:text=text[:15900]+' [Preview truncated; full bounded event retained locally.]'
                lines.append('line='+b64(text))
            if self.selected in self.partial:lines.append('line='+b64('Streaming: '+self.store.clean(self.partial[self.selected])))
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
                        except Exception:self.notice='Chat action rejected; check session, selection, message bounds and connection'
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
        key=os.environ.get('DEEPSEEK_API_KEY','')
        store=ChatStore(lock_path,secrets=[key],recover=True)
        try:
            # Do not give a child MCP process the provider credential.
            env={k:v for k,v in os.environ.items() if k not in {'DEEPSEEK_API_KEY','OPENAI_API_KEY','ANTHROPIC_API_KEY'}}
            env['SYX_STATE_DIR']=str(directory.absolute())
            params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],env=env)
            async with stdio_client(params) as (read,write):
                async with ClientSession(read,write) as mcp:
                    await mcp.initialize()
                    await Coordinator(store,mcp,directory,key).serve()
        finally:store.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir',default=os.environ.get('SYX_STATE_DIR',str(Path.home()/'.local/share/syx-assistant')))
    parser.add_argument('--history-dir',default=str(Path.home()/'.local/share/syx-assistant-chat'))
    args=parser.parse_args()
    try:asyncio.run(serve(args))
    except KeyboardInterrupt:pass


if __name__=='__main__':main()
