"""Developer-only persistence of observed unknown-Send notices, never delivery truth.

The parent still owns admission/deduplication. Only its bounded observation cache is
stored in a separate candidate table in disposable runtime history. No replay,
question/payload, request outcome, inference or production migration is added.
"""
from collections import OrderedDict

from dev.chat_recovery_candidate import RecoveryCoordinator
from syx_chat_store import identity


class DurableRecoveryCoordinator(RecoveryCoordinator):
    def __init__(self, store, mcp, state_dir, api_key):
        # Parent validates both disposable roots before touching history.
        super().__init__(store, mcp, state_dir, api_key)
        if store.db.execute('PRAGMA foreign_keys').fetchone() != (1,):
            raise ValueError('Candidate recovery requires enabled history foreign keys')
        with store.db:
            store.db.execute('''CREATE TABLE IF NOT EXISTS candidate_unknown_sends(
                position INTEGER PRIMARY KEY CHECK(position BETWEEN 0 AND 99),
                chat_id TEXT UNIQUE NOT NULL REFERENCES chats(chat_id) ON DELETE CASCADE,
                previous_turn_id TEXT,
                previous_status TEXT,
                CHECK((previous_turn_id IS NULL AND previous_status IS NULL) OR
                      (previous_turn_id IS NOT NULL AND previous_status IS NOT NULL AND previous_status IN
                       ('running','completed','failed','cancelled','interrupted'))))''')
        self._load_unknown()

    def _load_unknown(self):
        rows = self.store.db.execute('''SELECT u.chat_id,u.previous_turn_id,u.previous_status,
                c.provider,c.route,c.model
            FROM candidate_unknown_sends AS u LEFT JOIN chats AS c ON c.chat_id=u.chat_id
            ORDER BY u.position LIMIT 101''').fetchall()
        if len(rows) > self.MAX_UNKNOWN_CHATS:
            raise ValueError('Candidate recovery observations exceed the supported bound')
        restored = OrderedDict()
        for cid, turn, status, provider, route, model in rows:
            identity(cid)
            if (provider, route, model) != ('deepseek', 'api', 'deepseek-v4-pro'):
                raise ValueError('Candidate recovery observation has no supported chat')
            if turn is None:
                if status is not None:
                    raise ValueError('Invalid candidate recovery observation')
                previous = None
            else:
                identity(turn)
                if status not in {'running', 'completed', 'failed', 'cancelled', 'interrupted'}:
                    raise ValueError('Invalid candidate recovery observation')
                previous = (turn, status)
            restored[cid] = previous
        self.unknown_sends = restored
        return restored.copy()

    def _save_unknown(self, before):
        if self.unknown_sends == before:
            return
        try:
            # At most 100 rows; deletion and replacement commit or roll back together.
            # This is a single-owner coordinator seam, not concurrent-writer merging.
            with self.store.db:
                self.store.db.execute('DELETE FROM candidate_unknown_sends')
                self.store.db.executemany('''INSERT INTO candidate_unknown_sends
                    (position,chat_id,previous_turn_id,previous_status) VALUES(?,?,?,?)''',
                    ((position, cid, *(previous or (None, None)))
                     for position, (cid, previous) in enumerate(self.unknown_sends.items())))
        except Exception:
            self.unknown_sends = before
            raise

    async def dispatch(self, request):
        before = self._load_unknown()
        await super().dispatch(request)
        self._save_unknown(before)

    def recovery_notice(self):
        before = self._load_unknown()
        notice = super().recovery_notice()
        self._save_unknown(before)
        return notice
