"""Developer-only durable acceptance, never provider dispatch or normal migration.

The trusted admission wrapper obtains evidence from the owned MCP adapter. UI
requests supply exact IDs/text, never an arbitrary evidence JSON envelope.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
import sqlite3
import time

from syx_chat_store import now
from dev.chat_target_candidate import bounded, canonical, uuid, NOTICE, RETENTION_NOTICE
from dev.chat_target_transport import McpTargetDrafts

PAGE_KEYS = ('kind', 'capture', 'offset', 'limit', 'rows', 'next_offset')
LEASE_SECONDS = 2


def intent(chat_id, request_id, turn_id, game_session, text, attachment_ids):
    for value in (chat_id, request_id, turn_id, game_session): uuid(value)
    if type(text) is not str or not 1 <= len(text.strip()) <= len(text) <= 8000:
        raise ValueError('Question must contain 1..8000 characters')
    if not isinstance(attachment_ids, list) or len(attachment_ids) > 8:
        raise ValueError('Expected 0..8 attachment IDs')
    for aid in attachment_ids: uuid(aid)
    if len(set(attachment_ids)) != len(attachment_ids):
        raise ValueError('Duplicate requested attachment IDs')
    value = dict(chat_id=chat_id, request_id=request_id, turn_id=turn_id,
                 game_session=game_session, text=text, attachment_ids=list(attachment_ids))
    return value, sha256(canonical(value)).hexdigest()


class TargetQueue:
    """Explicit extension for disposable ChatStore databases, schema 1 retained.

    A queued turn is only durably accepted. No worker, provider claim/resume or
    paid exactly-once assertion is supplied. The production Conversation.run
    cannot consume these already-created turns without a reviewed integration.
    """
    def __init__(self, store, *, clock=time.monotonic):
        self.store, self.db, self.clock = store, store.db, clock

    @contextmanager
    def _transaction(self):
        if self.db.in_transaction:
            raise ValueError('Queue requires its own transaction')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise

    def _version(self):
        if self.db.execute('PRAGMA user_version').fetchone()[0] != 1:
            raise ValueError('Base history schema 1 required')
        if not self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='syx_ux_schema'").fetchone():
            return None
        row = self.db.execute("SELECT version FROM syx_ux_schema WHERE component='target_queue'").fetchone()
        if row is not None and row[0] != 1:
            raise ValueError('Unknown target queue extension version')
        return None if row is None else row[0]

    def initialize(self):
        with self._transaction():
            if self._version() is not None:
                return False
            if self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='syx_target_queue'").fetchone():
                raise ValueError('Unversioned target queue table; no migration attempted')
            self.db.execute('CREATE TABLE IF NOT EXISTS syx_ux_schema(component TEXT PRIMARY KEY,version INTEGER NOT NULL)')
            self.db.execute('''CREATE TABLE syx_target_queue(
                request_id TEXT PRIMARY KEY,turn_id TEXT NOT NULL UNIQUE,chat_id TEXT NOT NULL,
                game_session TEXT NOT NULL,intent_sha256 TEXT NOT NULL,envelope_sha256 TEXT NOT NULL,
                envelope TEXT NOT NULL,accepted_at TEXT NOT NULL,
                FOREIGN KEY(chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE,
                FOREIGN KEY(turn_id,chat_id) REFERENCES turns(turn_id,chat_id) ON DELETE CASCADE)''')
            self.db.execute('CREATE INDEX syx_target_pending_chats ON turns(chat_id,status)')
            self.db.execute("INSERT INTO syx_ux_schema VALUES('target_queue',1)")
        return True

    def _ready(self):
        if self._version() is None:
            raise ValueError('Explicit target queue initialization required')

    def _record(self, request_id):
        self._ready()
        row = self.db.execute('SELECT request_id,turn_id,chat_id,game_session,intent_sha256,envelope_sha256,envelope,accepted_at FROM syx_target_queue WHERE request_id=?', (request_id,)).fetchone()
        if row is None:
            return None
        result = dict(zip(('request_id','turn_id','chat_id','game_session','intent_sha256','envelope_sha256','envelope','accepted_at'), row))
        if sha256(result['envelope'].encode('utf-8')).hexdigest() != result['envelope_sha256']:
            raise ValueError('Accepted evidence integrity check failed')
        return result

    @staticmethod
    def _ack(row):
        envelope = json.loads(row['envelope'])
        return {key: row[key] for key in ('request_id','turn_id','chat_id','game_session','intent_sha256','envelope_sha256','accepted_at')} | {
            'accepted': True, 'provider_dispatch': 'not_implemented',
            'accepted_targets': [{'attachment_id': item['attachment_id'], 'observation_sha256': item['observation_sha256']}
                                 for item in envelope['attachments']]}

    def lookup(self, request):
        if self.db.in_transaction:
            raise ValueError('Acceptance lookup requires committed history state')
        return self._lookup_exact(request)

    def _lookup_exact(self, request):
        value, digest = intent(**request)
        row = self._record(value['request_id'])
        if row is None:
            return None
        if row['intent_sha256'] != digest:
            raise ValueError('Request already bound to a different send')
        return self._ack(row)

    def _envelope(self, request, envelope):
        """Structural/payload checks, not a substitute for the owned MCP read."""
        if not isinstance(envelope, dict):
            raise ValueError('Prepared evidence object required')
        raw = bounded(envelope)
        try:
            cleaned = self.store.clean(envelope)
        except RecursionError as error:
            raise ValueError('Prepared evidence is too nested; narrow fields') from error
        if cleaned != envelope or any(secret in raw.decode('utf-8') for secret in self.store.secrets):
            raise ValueError('Attachment includes credentials or private fields; choose different evidence')
        if (set(envelope) != {'schema','chat_id','notice','has_attachments','attachments','admission'}
                or envelope.get('schema') != 'syx-target-preview-1' or envelope.get('chat_id') != request['chat_id']
                or envelope.get('notice') != NOTICE or not isinstance(envelope.get('attachments'), list)
                or not all(isinstance(x, dict) for x in envelope['attachments'])
                or [x.get('attachment_id') for x in envelope['attachments']] != request['attachment_ids']
                or envelope.get('has_attachments') is not bool(request['attachment_ids'])):
            raise ValueError('Prepared target selection does not match the send')
        state = envelope.get('admission')
        if (not isinstance(state, dict) or set(state) != {'session_id','game_version','snapshot_id','tick','captured_at','scene','fresh','live','scope'}
                or state.get('session_id') != request['game_session']
                or state.get('fresh') is not True or state.get('live') is not True
                or state.get('scope') != 'recent_exporter_observation'):
            raise ValueError('Owned fresh runtime admission required')
        # Exporter observation IDs are opaque session:sequence strings, not UUIDs.
        if type(state.get('snapshot_id')) is not str or not 1 <= len(state['snapshot_id']) <= 160:
            raise ValueError('Original snapshot observation ID required')
        if (not isinstance(state.get('captured_at'), str) or not isinstance(state.get('game_version'), str)
                or not isinstance(state.get('scene'), dict)):
            raise ValueError('Admission time/version/scene required')
        for item in envelope['attachments']:
            if set(item) != set(PAGE_KEYS) | {'attachment_id','observation_sha256','retention_hint'} or not isinstance(item.get('capture'), dict):
                raise ValueError('Prepared target provenance required')
            hint = item.get('retention_hint')
            if (not isinstance(hint, dict) or set(hint) != {'remaining_seconds_at_stage','notice'}
                    or hint['notice'] != RETENTION_NOTICE or type(hint['remaining_seconds_at_stage']) not in (int,float)
                    or not 0 <= hint['remaining_seconds_at_stage'] <= 120):
                raise ValueError('Original staged retention hint required')
            page = {key: item[key] for key in PAGE_KEYS}
            meta = item['capture']
            if (sha256(canonical(page)).hexdigest() != item.get('observation_sha256')
                    or meta.get('session_id') != request['game_session'] or meta.get('game_version') != state.get('game_version')
                    or canonical(meta.get('scene')) != canonical(state.get('scene'))):
                raise ValueError('Prepared target provenance/hash does not match admission')
        return raw

    def _enqueue_prepared(self, request, envelope, prepared_at):
        """Trusted wrapper only; no UI/MCP endpoint accepts raw prepared JSON."""
        value, digest = intent(**request)
        try:
            with self._transaction():
                prior = self._lookup_exact(value)
                if prior is not None:
                    return prior
                if self.store.clean(value['text']) != value['text'] or any(secret in value['text'] for secret in self.store.secrets):
                    raise ValueError('Enter credentials through connection setup, not chat')
                raw = self._envelope(value, envelope)
                chat = self.store.chat(value['chat_id'])
                if (chat['provider'], chat['route'], chat['model']) != ('deepseek','api','deepseek-v4-pro'):
                    raise ValueError('Only the simple Pro route is admitted')
                if chat['attached_session'] != value['game_session']:
                    raise ValueError('Chat attachment changed; review current game')
                elapsed = self.clock() - prepared_at
                stamp = datetime.fromisoformat(envelope['admission']['captured_at'].replace('Z','+00:00'))
                if stamp.utcoffset() is None:
                    raise ValueError('Admission timestamp must include timezone')
                age = (datetime.now(timezone.utc) - stamp).total_seconds()
                if not 0 <= elapsed < LEASE_SECONDS or not -5 <= age <= 30:
                    raise ValueError('Admission lease/export expired; prepare again explicitly')
                if self.db.execute("SELECT 1 FROM turns WHERE chat_id=? AND status IN ('queued','running') LIMIT 1", (value['chat_id'],)).fetchone():
                    raise ValueError('This chat already has an accepted or running question')
                self.db.execute('INSERT INTO turns VALUES(?,?,?,?)', (value['turn_id'],value['chat_id'],value['game_session'],'queued'))
                # _event performs no transaction/commit; our one transaction owns both events.
                self.store._event(value['chat_id'],value['turn_id'],value['game_session'],'user',{'text':value['text']})
                self.store._event(value['chat_id'],value['turn_id'],value['game_session'],'target_evidence',{'envelope':json.loads(raw)})
                self.db.execute('INSERT INTO syx_target_queue VALUES(?,?,?,?,?,?,?,?)',
                    (value['request_id'],value['turn_id'],value['chat_id'],value['game_session'],digest,sha256(raw).hexdigest(),raw.decode('utf-8'),now()))
                return self._ack(self._record(value['request_id']))
        except sqlite3.Error as error:
            raise ValueError('History queue conflict or unavailable; no partial turn accepted') from error

    def cancel(self, request):
        """Cancel an accepted, undispatched question without deleting evidence."""
        with self._transaction():
            ack = self._lookup_exact(request)
            if ack is None:
                raise ValueError('No accepted request to cancel')
            row = self.db.execute('SELECT status FROM turns WHERE turn_id=? AND chat_id=?',
                                  (ack['turn_id'], ack['chat_id'])).fetchone()
            if row[0] == 'cancelled':
                return False
            if row[0] != 'queued':
                raise ValueError('Only an undispatched queued question can be cancelled')
            self.db.execute("UPDATE turns SET status='cancelled' WHERE turn_id=? AND chat_id=?", (ack['turn_id'], ack['chat_id']))
            self.store._event(ack['chat_id'], ack['turn_id'], ack['game_session'], 'turn_cancelled',
                              {'message': 'Accepted question cancelled before dispatch; no inference call'})
            return True

    def accepted_evidence(self, request_id):
        if self.db.in_transaction:
            raise ValueError('Accepted evidence requires committed history state')
        uuid(request_id)
        row = self._record(request_id)
        if row is None:
            raise ValueError('No accepted target request')
        return json.loads(row['envelope'])


class TargetAdmission:
    """Owned helper path: exact UI intent -> actual MCP -> atomic history -> ack.

    Does not run Conversation, inference, queue workers or gameplay commands.
    Acceptance and chip acknowledgement are separate so lost acks can be retried.
    """
    def __init__(self, queue, adapter):
        if not isinstance(queue, TargetQueue) or not isinstance(adapter, McpTargetDrafts):
            raise ValueError('Owned queue and MCP target adapter required')
        self.queue, self.adapter = queue, adapter

    async def accept(self, chat_id, request_id, turn_id, game_session, text, attachment_ids):
        request, _ = intent(chat_id, request_id, turn_id, game_session, text, attachment_ids)
        prior = self.queue.lookup(request)
        if prior is not None:
            return prior  # durable accepted receipt, not fresh/living capture authority
        try:
            envelope = await self.adapter.prepare(request['chat_id'], expected_session=request['game_session'], expected_ids=request['attachment_ids'])
            prepared_at = self.queue.clock()
            # No await between final preparation and transaction/lease check.
            return self.queue._enqueue_prepared(request, envelope, prepared_at)
        except Exception:
            # Another exact request can commit/ack while this one awaits MCP.
            # Recheck durable acceptance; cancellation still propagates.
            prior = self.queue.lookup(request)
            if prior is not None:
                return prior
            raise

    async def acknowledge(self, request):
        ack = self.queue.lookup(request)
        if ack is None:
            raise ValueError('No durable acceptance; draft targets retained')
        await self.adapter.clear_accepted(ack['chat_id'], ack['accepted_targets'])
        return ack
