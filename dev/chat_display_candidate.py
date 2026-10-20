"""Unshipped protocol-3 display/receipt broker, for disposable histories only.

No game API, provider, file watcher or automatic migration. Caller supplies real
fresh MCP presence for acknowledgements; this validates provenance, not visibility.
"""
from collections import OrderedDict
from dataclasses import dataclass
import base64
import time
from uuid import uuid4

from dev.chat_history_candidate import HistoryCandidate
from syx_chat_store import identity


@dataclass(frozen=True)
class Issued:
    at: float
    chat: str | None
    runtime: str | None
    events: dict
    body: tuple
    raw: bytes


class DisplayBroker:
    PROTOCOL=3
    WIRE_CAP=240000
    ACK_CAP=16384
    FRAME_CAP=8
    TTL=30
    ROW_CAP=100

    def __init__(self,store,*,clock=time.monotonic,epoch=None):
        self.store=store;self.history=HistoryCandidate(store);self.clock=clock
        self.epoch=identity(epoch or str(uuid4()));self.frames=OrderedDict();self.last=None
        self._cache_key=None;self._cache_value=None
        self._encoded_rows=None;self._encoded_value=()

    def _prune(self):
        at=self.clock()
        for key,frame in list(self.frames.items()):
            if at-frame.at>=self.TTL or at<frame.at:del self.frames[key]
        while len(self.frames)>self.FRAME_CAP:self.frames.popitem(last=False)

    def _state(self,chat_id):
        db=self.store.db
        if db.in_transaction:raise ValueError('Display candidate needs its own read transaction')
        db.execute('BEGIN')
        try:
            self.history._ready()
            completed=self.history._completed(simple=True)
            eligible="c.provider='deepseek' AND c.route='api' AND c.model='deepseek-v4-pro'"
            read=db.execute('''SELECT r.chat_id,r.turn_id FROM syx_ux_reads r
              JOIN chats c ON c.chat_id=r.chat_id WHERE '''+eligible+' LIMIT ?',
                (self.history.ROW_CAP+1,)).fetchall()
            if len(read)>self.history.ROW_CAP:raise ValueError('Receipt metadata budget exceeded')
            seen=set(read);counts={}
            for key,item in completed.items():
                if key not in seen:counts[item['chat_id']]=counts.get(item['chat_id'],0)+1
            rows=[]
            if chat_id is not None:
                chat=self.store.chat(chat_id)
                if (chat['provider'],chat['route'],chat['model'])!=('deepseek','api','deepseek-v4-pro'):
                    raise ValueError('Display candidate is restricted to simple Pro chats')
                sizes=db.execute('SELECT sequence,length(CAST(payload AS BLOB)) FROM events WHERE chat_id=? ORDER BY sequence DESC LIMIT ?',
                    (chat_id,self.ROW_CAP)).fetchall()
                if sum(r[1] for r in sizes)>self.history.BYTE_CAP:raise ValueError('Preview payload budget exceeded')
                after=min((r[0] for r in sizes),default=1)-1
                if db.execute('SELECT 1 FROM events WHERE chat_id=? AND sequence<=? LIMIT 1',(chat_id,after)).fetchone():
                    rows.append(('[Earlier events retained locally; latest 100 events shown.]',None))
                for event in self.store.events(chat_id,after=after,limit=self.ROW_CAP):
                    kind=event['kind'];payload=event['payload'];receipt=None
                    if kind in {'user','assistant'}:
                        text=payload.get('text','')
                        if not isinstance(text,str):raise ValueError('Invalid preview text')
                        if not text:continue
                        text=('You: ' if kind=='user' else 'Assistant: ')+self.store.clean(text)
                        if event['game_session']!=chat['attached_session']:text='Earlier game · '+text
                        final=completed.get((chat_id,event['turn_id']))
                        if kind=='assistant' and final and final['event_id']==event['event_id'] and (chat_id,event['turn_id']) not in seen:
                            receipt=(identity(event['event_id']),identity(event['turn_id']),identity(event['game_session']),final['payload_sha256'])
                    elif kind in {'turn_error','turn_cancelled'}:text='Reply interrupted. Please try again or start a new chat.'
                    elif kind=='session_boundary':text='Connected to this game. Earlier messages are history.'
                    else:continue
                    rows.append((text,receipt))
            db.commit()
            return counts,rows
        except BaseException:
            db.rollback();raise

    def _issue(self,chat_id,runtime,counts,rows,*,available):
        self._prune()
        header=['protocol=3','epoch='+self.epoch,'counts='+('ready' if available else 'unavailable')]
        if available:header.append('unread_total='+str(sum(counts.values())))
        if chat_id is not None:header.append('chat='+identity(chat_id))
        if runtime is not None:header.append('runtime='+identity(runtime))
        # Bound metadata independently of payload; total count is all eligible chats.
        if available:
            chosen=sorted(counts.items())
            if chat_id is not None:chosen=[(chat_id,counts.get(chat_id,0))]+[(cid,n) for cid,n in chosen if cid!=chat_id]
            header.append('chat_counts_complete='+str(len(chosen)<=self.ROW_CAP).lower())
            header.append('unread_chat_count='+str(len(counts)))
            for cid,count in chosen[:self.ROW_CAP]:header.append('chat_unread='+identity(cid)+'|'+str(count))
        if rows is not self._encoded_rows:
            self._encoded_value=tuple(('line='+base64.b64encode(text.encode()).decode('ascii'),item) for text,item in rows)
            self._encoded_rows=rows
        encoded=list(self._encoded_value)
        omitted=False
        while True:
            lines=list(header);events={}
            if omitted:lines.append('omitted=true')
            for index,(line,receipt) in enumerate(encoded):
                lines.append(line)
                if receipt is not None and runtime is not None and available:
                    eid,tid,session,payload_hash=receipt
                    lines.append('reply='+str(index)+'|'+eid+'|'+tid+'|'+session+'|'+payload_hash)
                    events[eid]=(tid,session,payload_hash)
            body=tuple(lines)
            # Reserve the exact fixed-width frame field before accepting this body.
            if sum(len(line)+1 for line in lines)+43<=self.WIRE_CAP:break
            if not encoded:raise ValueError('Display metadata exceeds wire budget')
            encoded=encoded[1:];omitted=True
        if self.last in self.frames and self.frames[self.last].body==body:
            return self.frames[self.last].raw
        frame=str(uuid4());raw=('\n'.join([*lines,'frame='+frame])+'\n').encode('ascii')
        self.frames[frame]=Issued(self.clock(),chat_id,runtime,events,body,raw);self.last=frame;self._prune()
        return raw

    def publish(self,chat_id,runtime):
        if chat_id is not None:identity(chat_id)
        if runtime is not None:identity(runtime)
        key=(chat_id,self.store.db.total_changes,self.store.db.execute('PRAGMA data_version').fetchone()[0],self.history.ROW_CAP,self.history.BYTE_CAP,self.ROW_CAP)
        if key!=self._cache_key:
            counts,rows=self._state(chat_id)
            self._cache_value=(counts,tuple(rows));self._cache_key=key
        counts,rows=self._cache_value
        return self._issue(chat_id,runtime,counts,rows,available=True)

    def unavailable(self,runtime):
        """Explicit unknown, never a zero count or a source of read eligibility."""
        if runtime is not None:identity(runtime)
        return self._issue(None,runtime,{},[],available=False)

    @classmethod
    def parse_receipt(cls,raw):
        if not isinstance(raw,bytes) or not 1<=len(raw)<=cls.ACK_CAP:raise ValueError('Receipt exceeds bounds')
        if not raw.endswith(b'\n') or any(b!=10 and not 32<=b<=126 for b in raw):raise ValueError('Canonical ASCII LF receipt required')
        fields={};events=[]
        try:
            for line in raw.decode('ascii').splitlines():
                key,sep,value=line.partition('=')
                if not sep:raise ValueError('Invalid receipt')
                if key=='event':events.append(identity(value));continue
                if key not in {'protocol','epoch','frame','request','runtime','chat','observed_session'} or key in fields:
                    raise ValueError('Unexpected/duplicate receipt field')
                fields[key]=value
        except UnicodeError:raise ValueError('ASCII receipt required') from None
        if fields.keys()!={'protocol','epoch','frame','request','runtime','chat','observed_session'} or fields['protocol']!='3':
            raise ValueError('Paired receipt protocol 3 required')
        for key,value in fields.items():
            if key!='protocol':identity(value)
        if not 1<=len(events)<=100:raise ValueError('Acknowledge 1..100 explicit final events')
        return fields,events

    def acknowledge(self,raw,*,presence):
        fields,events=self.parse_receipt(raw);self._prune()
        if fields['epoch']!=self.epoch or fields['frame'] not in self.frames:raise ValueError('Expired or restarted display frame')
        frame=self.frames[fields['frame']]
        if fields['chat']!=frame.chat or fields['runtime']!=frame.runtime:raise ValueError('Display chat/runtime mismatch')
        if not isinstance(presence,dict) or presence.get('session_id')!=frame.runtime or presence.get('fresh') is not True or presence.get('live') is not True:
            raise ValueError('Fresh matching MCP presence required for receipt')
        if any(eid not in frame.events or frame.events[eid][1]!=fields['observed_session'] for eid in events):
            raise ValueError('Receipt includes a reply not issued in this chat/session/frame')
        inserted=self.history.acknowledge(fields['chat'],fields['observed_session'],events,
            expected_payloads={eid:frame.events[eid][2] for eid in events})
        return dict(request=fields['request'],status='applied',newly_read=inserted)


def receipt(frame,events,observed_session,*,request=None):
    """Test/native-adapter wire helper; not a claim these events were displayed."""
    values={}
    for line in frame.decode('ascii').splitlines():
        key,_,value=line.partition('=')
        if key in {'epoch','frame','runtime','chat'}:values[key]=value
    if values.keys()!={'epoch','frame','runtime','chat'}:raise ValueError('Selected chat/runtime display frame required')
    lines=['protocol=3',*('='.join((k,v)) for k,v in values.items()),'request='+identity(request or str(uuid4())),
        'observed_session='+identity(observed_session),*('event='+identity(eid) for eid in events)]
    return ('\n'.join(lines)+'\n').encode('ascii')
