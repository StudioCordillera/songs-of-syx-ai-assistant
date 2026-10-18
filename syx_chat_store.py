"""Local conversation/event storage. Runtime game sessions are not permanent save identities."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from uuid import UUID, uuid4


def identity(value):
    if not isinstance(value,str) or str(UUID(value))!=value:
        raise ValueError('Canonical UUID required')
    return value


def now():
    return datetime.now(timezone.utc).isoformat()


class ChatStore:
    def __init__(self,directory,secrets=(),recover=False):
        self.directory=Path(directory)
        if self.directory.is_symlink():raise ValueError('History directory must not be a symlink')
        self.directory.mkdir(parents=True,exist_ok=True,mode=0o700);self.directory.chmod(0o700)
        self.secrets=tuple(s for s in secrets if s)
        path=self.directory/'history.sqlite3'
        if path.is_symlink():raise ValueError('History database must not be a symlink')
        self.db=sqlite3.connect(path)
        path.chmod(0o600)
        version=self.db.execute('PRAGMA user_version').fetchone()[0]
        if version not in {0,1}:
            self.db.close()
            raise ValueError('Unsupported history schema version')
        self.db.executescript('''PRAGMA foreign_keys=ON; PRAGMA journal_mode=WAL; PRAGMA temp_store=MEMORY;
        CREATE TABLE IF NOT EXISTS chats(
          chat_id TEXT PRIMARY KEY,title TEXT NOT NULL,attached_session TEXT NOT NULL,
          provider TEXT NOT NULL,model TEXT NOT NULL,route TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS turns(
          turn_id TEXT PRIMARY KEY,chat_id TEXT NOT NULL,game_session TEXT NOT NULL,status TEXT NOT NULL,
          UNIQUE(turn_id,chat_id),FOREIGN KEY(chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS events(
          sequence INTEGER PRIMARY KEY,event_id TEXT UNIQUE NOT NULL,chat_id TEXT NOT NULL,turn_id TEXT,
          game_session TEXT NOT NULL,at TEXT NOT NULL,kind TEXT NOT NULL,payload TEXT NOT NULL,
          FOREIGN KEY(chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE,
          FOREIGN KEY(turn_id,chat_id) REFERENCES turns(turn_id,chat_id) ON DELETE CASCADE);
        ''')
        # A process restart cannot transparently resume a provider stream/tool subturn.
        if recover:
            with self.db:
                self.db.execute("UPDATE turns SET status='interrupted' WHERE status='running'")
        self.db.execute('PRAGMA user_version=1')

    def close(self):
        self.db.close()

    def clean(self,value):
        if isinstance(value,str):
            for secret in self.secrets:value=value.replace(secret,'[credential redacted]')
            return value
        if isinstance(value,list):return [self.clean(v) for v in value]
        if isinstance(value,dict):
            hidden={'reasoning_content','reasoning','authorization','api_key','access_token','refresh_token'}
            return {str(k):self.clean(v) for k,v in value.items() if str(k).lower() not in hidden}
        return value

    def chat(self,chat_id):
        identity(chat_id)
        row=self.db.execute('SELECT * FROM chats WHERE chat_id=?',(chat_id,)).fetchone()
        if row is None:raise ValueError('Chat not found')
        return dict(zip(['chat_id','title','attached_session','provider','model','route','created_at'],row))

    def new(self,game_session,title='New chat',provider='deepseek',model='deepseek-flash',route='api'):
        identity(game_session)
        if not isinstance(title,str) or not 1<=len(title.strip())<=100:raise ValueError('Chat title must contain 1..100 characters')
        supported={('deepseek','api'):{'deepseek-flash','deepseek-v4-pro'},('claude','subscription'):{'haiku','sonnet','opus'},('claude','api'):{'haiku','sonnet','opus'}}
        if model not in supported.get((provider,route),set()):
            raise ValueError('Unsupported explicit provider/model/route; no fallback is available')
        cid=str(uuid4())
        with self.db:self.db.execute('INSERT INTO chats VALUES(?,?,?,?,?,?,?)',(cid,self.clean(title.strip()),game_session,provider,model,route,now()))
        return self.chat(cid)

    def list(self,game_session=None):
        if game_session is not None:identity(game_session)
        rows=self.db.execute('SELECT chat_id FROM chats '+('WHERE attached_session=? ' if game_session else '')+'ORDER BY created_at DESC LIMIT 100',
            (game_session,) if game_session else ()).fetchall()
        return [self.chat(r[0]) for r in rows]

    def _event(self,chat_id,turn_id,game_session,kind,payload):
        chat=self.chat(chat_id)
        payload=dict(payload,provider=chat['provider'],model=chat['model'],route=chat['route'])
        raw=json.dumps(self.clean(payload),ensure_ascii=False,separators=(',',':'),allow_nan=False)
        if len(raw.encode())>262144:raise ValueError('History event exceeds 256 KiB')
        self.db.execute('INSERT INTO events(event_id,chat_id,turn_id,game_session,at,kind,payload) VALUES(?,?,?,?,?,?,?)',
            (str(uuid4()),chat_id,turn_id,game_session,now(),kind,raw))

    def append(self,chat_id,turn_id,game_session,kind,payload):
        self.chat(chat_id);identity(game_session)
        if turn_id is not None:
            identity(turn_id)
            row=self.db.execute('SELECT game_session FROM turns WHERE turn_id=? AND chat_id=?',(turn_id,chat_id)).fetchone()
            if row is None or row[0]!=game_session:raise ValueError('History event must match its turn chat and game session')
        if kind not in {'tool','assistant','context_reset','session_boundary','turn_error','turn_cancelled'}:raise ValueError('Unknown history event kind')
        with self.db:self._event(chat_id,turn_id,game_session,kind,payload)

    def attach(self,chat_id,game_session):
        chat=self.chat(chat_id);identity(game_session)
        with self.db:
            self._event(chat_id,None,game_session,'session_boundary',{'previous_session':chat['attached_session'],'current_session':game_session,'explicit_continuation':True})
            self.db.execute('UPDATE chats SET attached_session=? WHERE chat_id=?',(game_session,chat_id))
        return self.chat(chat_id)

    def begin(self,chat_id,turn_id,game_session,text):
        chat=self.chat(chat_id);identity(turn_id);identity(game_session)
        if chat['attached_session']!=game_session:raise ValueError('Continue this chat in the new game session explicitly first')
        if not isinstance(text,str) or not 1<=len(text.strip())<=8000:raise ValueError('Message must contain 1..8000 characters')
        if any(secret in text for secret in self.secrets):raise ValueError('Enter credentials through connection setup, not chat')
        try:
            with self.db:
                self.db.execute('INSERT INTO turns VALUES(?,?,?,?)',(turn_id,chat_id,game_session,'running'))
                self._event(chat_id,turn_id,game_session,'user',{'text':text,'provider':chat['provider'],'model':chat['model'],'route':chat['route']})
        except sqlite3.IntegrityError as error:raise ValueError('Turn already exists; it will not be sent again') from error

    def finish(self,chat_id,turn_id,status):
        if status not in {'completed','failed','cancelled'}:raise ValueError('Invalid turn status')
        with self.db:
            cursor=self.db.execute("UPDATE turns SET status=? WHERE chat_id=? AND turn_id=? AND status='running'",(status,chat_id,turn_id))
            if cursor.rowcount!=1:raise ValueError('Turn is not running in this chat')

    def events(self,chat_id,after=0,limit=100):
        self.chat(chat_id)
        if type(after) is not int or after<0 or type(limit) is not int or not 1<=limit<=1000:raise ValueError('Invalid history page')
        rows=self.db.execute('SELECT sequence,event_id,turn_id,game_session,at,kind,payload FROM events WHERE chat_id=? AND sequence>? ORDER BY sequence LIMIT ?',
            (chat_id,after,limit)).fetchall()
        return [dict(zip(['sequence','event_id','turn_id','game_session','at','kind'],r[:6]),payload=json.loads(r[6])) for r in rows]

    def turns(self,chat_id):
        self.chat(chat_id)
        return [dict(turn_id=r[0],game_session=r[1],status=r[2]) for r in self.db.execute('SELECT turn_id,game_session,status FROM turns WHERE chat_id=? ORDER BY rowid',(chat_id,))]

    def delete(self,chat_id):
        self.chat(chat_id)
        with self.db:self.db.execute('DELETE FROM chats WHERE chat_id=?',(chat_id,))

    def rename(self,chat_id,title):
        self.chat(chat_id)
        if not isinstance(title,str) or not 1<=len(title.strip())<=100:raise ValueError('Chat title must contain 1..100 characters')
        with self.db:self.db.execute('UPDATE chats SET title=? WHERE chat_id=?',(self.clean(title.strip()),chat_id))
        return self.chat(chat_id)

    def export(self,chat_id):
        """Explicit local export. No game saves or provider continuation are included."""
        chat=self.chat(chat_id)
        rows=self.db.execute('SELECT count(*) FROM events WHERE chat_id=?',(chat_id,)).fetchone()[0]
        if rows>10000:raise ValueError('Chat exceeds the 10000-event export limit')
        events=[];after=0;budget=0
        while True:
            page=self.events(chat_id,after,25)
            if not page:break
            budget+=sum(len(json.dumps(row,ensure_ascii=False).encode()) for row in page)
            if budget>10*1024*1024:raise ValueError('Chat exceeds the 10 MiB export limit')
            events.extend(page);after=page[-1]['sequence']
        raw=json.dumps(self.clean(dict(schema_version=1,chat=chat,turns=self.turns(chat_id),events=events)),ensure_ascii=False,allow_nan=False,indent=2).encode()
        if len(raw)>10*1024*1024:raise ValueError('Chat exceeds the 10 MiB export limit')
        directory=self.directory/'exports'
        if directory.is_symlink():raise ValueError('Export directory cannot be a symlink')
        directory.mkdir(exist_ok=True,mode=0o700);directory.chmod(0o700)
        import os
        temporary=directory/(chat_id+'.tmp')
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as file:file.write(raw)
        target=directory/(chat_id+'.json');os.replace(temporary,target)
        return target
