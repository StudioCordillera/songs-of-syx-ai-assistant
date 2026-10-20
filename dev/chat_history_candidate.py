"""Developer-only unread/history candidate; NOT imported or packaged by the player.

Explicitly migrate only disposable test databases. No CLI, inference, game API,
UI/display assertion, automatic attachment or permanent world identity is supplied.
Read receipts identify individual displayed final events, never a global high-water
sequence that could clear another chat or a reply completed out of order.
"""
import hashlib
import json

from syx_chat_store import identity


class HistoryCandidate:
    ROW_CAP = 10000
    BYTE_CAP = 2 * 1024 * 1024

    def __init__(self, store):
        self.store = store
        self.db = store.db

    def _begin(self):
        if self.db.in_transaction:
            raise ValueError('Candidate requires its own transaction; nested admission is unsupported')
        self.db.execute('BEGIN IMMEDIATE')

    def _version(self):
        if self.db.execute('PRAGMA user_version').fetchone()[0] != 1:
            raise ValueError('Candidate requires the unchanged base history schema 1')
        exists = self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='syx_ux_schema'").fetchone()
        if not exists:
            return None
        row = self.db.execute("SELECT version FROM syx_ux_schema WHERE component='receipts'").fetchone()
        if row is None or row[0] != 1:
            raise ValueError('Unknown candidate receipt extension version')
        return row[0]

    def _completed(self, chat_id=None, *, simple=False):
        """Bounded metadata scan; refusal is not a partial/zero unread result."""
        if type(simple) is not bool:raise ValueError('Explicit simple-mode filter required')
        sql = '''SELECT e.sequence,e.event_id,e.chat_id,e.turn_id,e.game_session,e.payload
          FROM events e JOIN turns t ON t.turn_id=e.turn_id AND t.chat_id=e.chat_id
          JOIN chats c ON c.chat_id=e.chat_id
          WHERE e.kind='assistant' AND t.status='completed' AND e.game_session=t.game_session'''
        if simple:
            sql += " AND c.provider='deepseek' AND c.route='api' AND c.model='deepseek-v4-pro'"
        if chat_id is not None:
            sql += ' AND e.chat_id=?'
        sql += ' ORDER BY e.sequence LIMIT ?'
        args = (chat_id, self.ROW_CAP + 1) if chat_id is not None else (self.ROW_CAP + 1,)
        latest = {}
        size = 0
        for count, row in enumerate(self.db.execute(sql, args), 1):
            size += len(row[5].encode('utf-8'))
            if count > self.ROW_CAP or size > self.BYTE_CAP:
                raise ValueError('History candidate scan budget exceeded; no complete result established')
            payload = json.loads(row[5])
            if not isinstance(payload, dict):
                raise ValueError('Invalid history payload')
            text = payload.get('text')
            if payload.get('completed') is True and isinstance(text, str) and text.strip():
                latest[(row[2], row[3])] = {
                    'sequence': row[0], 'event_id': row[1], 'chat_id': row[2],
                    'turn_id': row[3], 'game_session': row[4],
                    'payload_sha256': hashlib.sha256(row[5].encode('utf-8')).hexdigest()}
        return latest

    def initialize(self):
        """One explicit transaction; baseline existing completed replies as read.

        No ChatStore method with its own transaction is called inside this one.
        Pending/interrupted/empty/failed replies are not baselined as completions.
        Repeated initialization never marks newly arrived replies read.
        """
        self._begin()
        try:
            if self._version() is not None:
                self.db.commit()
                return False
            completed = self._completed()
            self.db.execute('''CREATE TABLE syx_ux_schema(
                component TEXT PRIMARY KEY,version INTEGER NOT NULL)''')
            self.db.execute('''CREATE TABLE syx_ux_reads(
                chat_id TEXT NOT NULL,turn_id TEXT NOT NULL,event_id TEXT NOT NULL UNIQUE,
                PRIMARY KEY(chat_id,turn_id),
                FOREIGN KEY(chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE,
                FOREIGN KEY(turn_id,chat_id) REFERENCES turns(turn_id,chat_id) ON DELETE CASCADE,
                FOREIGN KEY(event_id) REFERENCES events(event_id) ON DELETE CASCADE)''')
            self.db.execute('CREATE INDEX syx_ux_events_chat_turn ON events(chat_id,turn_id,sequence)')
            self.db.execute("INSERT INTO syx_ux_schema VALUES('receipts',1)")
            self.db.executemany('INSERT INTO syx_ux_reads VALUES(?,?,?)',
                [(r['chat_id'], r['turn_id'], r['event_id']) for r in completed.values()])
            self.db.commit()
            return True
        except BaseException:
            self.db.rollback()
            raise

    def _ready(self):
        if self._version() is None:
            raise ValueError('Explicit candidate initialization required')

    def unread(self, chat_id):
        identity(chat_id)
        # One SQLite read transaction sees event/turn completion and receipts together.
        if self.db.in_transaction:
            raise ValueError('Nested candidate read is unsupported')
        self.db.execute('BEGIN')
        try:
            self._ready()
            self.store.chat(chat_id)
            rows = self._completed(chat_id)
            seen = {r[0] for r in self.db.execute('SELECT turn_id FROM syx_ux_reads WHERE chat_id=?', (chat_id,))}
            result = [r for r in rows.values() if r['turn_id'] not in seen]
            self.db.commit()
            return result
        except BaseException:
            self.db.rollback()
            raise

    def acknowledge(self, chat_id, observed_session, event_ids, *, expected_payloads=None):
        """Caller must supply ONLY actually displayed event IDs from one session.

        This candidate validates provenance/completion, not physical visibility.
        Invalid/stale/wrong-chat batches fail atomically without clearing anything.
        Different historical-session rows need separate display acknowledgements.
        """
        identity(chat_id)
        identity(observed_session)
        if not isinstance(event_ids, (list, tuple)) or not 1 <= len(event_ids) <= 100:
            raise ValueError('Acknowledge 1..100 displayed event UUIDs')
        for eid in event_ids:
            identity(eid)
        requested = set(event_ids)
        if expected_payloads is not None:
            if not isinstance(expected_payloads,dict) or set(expected_payloads)!=requested or any(not isinstance(v,str) or len(v)!=64 or any(c not in '0123456789abcdef' for c in v) for v in expected_payloads.values()):
                raise ValueError('Exact issued payload hashes required')
        self._begin()
        try:
            self._ready()
            self.store.chat(chat_id)
            rows = {r['event_id']: r for r in self._completed(chat_id).values()}
            if any(eid not in rows or rows[eid]['game_session'] != observed_session for eid in requested):
                raise ValueError('Read acknowledgement is not a completed visible reply in this chat/session')
            if expected_payloads is not None and any(rows[eid]['payload_sha256']!=expected_payloads[eid] for eid in requested):
                raise ValueError('Displayed reply payload changed; no acknowledgement recorded')
            inserted = 0
            for eid in sorted(requested):
                r = rows[eid]
                inserted += self.db.execute('''INSERT INTO syx_ux_reads VALUES(?,?,?)
                    ON CONFLICT(chat_id,turn_id) DO NOTHING''',
                    (chat_id, r['turn_id'], eid)).rowcount
            self.db.commit()
            return inserted
        except BaseException:
            self.db.rollback()
            raise

    def chats(self, session=None, scope='attached', simple=True, limit=100):
        """Runtime filters before LIMIT; no inferred save/world identity.

        `history` includes observed event sessions even after explicit reattachment.
        `attached` names only the current mutable runtime attachment. No provider
        change or automatic attachment is performed by this read-only selection.
        """
        if session is not None:
            identity(session)
        if scope not in {'attached', 'history'} or type(simple) is not bool or type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('Invalid runtime history selection')
        predicates, args = [], []
        if simple:
            predicates.append("provider='deepseek' AND route='api' AND model='deepseek-v4-pro'")
        if session is not None:
            if scope == 'attached':
                predicates.append('attached_session=?')
                args.append(session)
            else:
                predicates.append('''(attached_session=? OR EXISTS(
                    SELECT 1 FROM events e WHERE e.chat_id=c.chat_id AND e.game_session=?))''')
                args.extend((session, session))
        fields = ['chat_id', 'title', 'attached_session', 'provider', 'model', 'route', 'created_at']
        sql = 'SELECT ' + ','.join('c.' + name for name in fields) + ' FROM chats c'
        if predicates:
            sql += ' WHERE ' + ' AND '.join(predicates)
        sql += ' ORDER BY created_at DESC,chat_id DESC LIMIT ?'
        return [dict(zip(fields, row)) for row in self.db.execute(sql, (*args, limit))]
