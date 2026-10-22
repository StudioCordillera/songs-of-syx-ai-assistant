"""Developer-only, plain recovery notices beside the unchanged simple coordinator.

No action resubmission, new history fields, inference, receipt or game API is added.
Construction requires caller-owned disposable state/history under runtime/.
"""
from collections import OrderedDict
from syx_chat_service import Coordinator
from dev.blueprint_mcp_candidate import isolated_state_dir

INTERRUPTED = 'Earlier reply interrupted; no automatic retry.'
UNKNOWN = 'Repeated request ID; original outcome unknown. No automatic retry.'


class RecoveryCoordinator(Coordinator):
    MAX_UNKNOWN_CHATS = 100
    TURN_INDEX = 'recovery_candidate_turns_chat'
    LATEST_TURN_SQL = ('SELECT turn_id,status FROM turns '
                       'INDEXED BY recovery_candidate_turns_chat '
                       'WHERE chat_id=? ORDER BY rowid DESC LIMIT 1')

    def __init__(self, store, mcp, state_dir, api_key):
        directory = isolated_state_dir(str(state_dir))
        isolated_state_dir(str(store.directory))
        # One-time candidate-only history index construction can scan existing turns.
        # Thereafter SQLite seeks this chat and walks its implicit rowid backwards;
        # unrelated chats do not get scanned on each UI refresh. No result cache.
        with store.db:
            store.db.execute('CREATE INDEX IF NOT EXISTS recovery_candidate_turns_chat ON turns(chat_id)')
            shape = store.db.execute('PRAGMA index_xinfo(recovery_candidate_turns_chat)').fetchall()
            definitions = store.db.execute('PRAGMA index_list(turns)').fetchall()
            if (shape != [(0, 1, 'chat_id', 0, 'BINARY', 1), (1, -1, None, 0, 'BINARY', 0)] or
                    not any(row[1] == self.TURN_INDEX and row[2] == 0 and row[4] == 0
                            for row in definitions)):
                raise ValueError('Unexpected candidate recovery turn index; history left intact')
        super().__init__(store, mcp, directory, api_key, simple=True)
        # Reconstructed only from an observed duplicate Send, never guessed from an ack.
        self.unknown_sends = OrderedDict()

    def latest_turn(self, chat):
        return self.store.db.execute(self.LATEST_TURN_SQL, (chat,)).fetchone()

    async def dispatch(self, request):
        rid, cid = request['request_id'], request.get('chat_id')
        duplicate = self.store.db.execute('SELECT 1 FROM actions WHERE request_id=?', (rid,)).fetchone()
        missing = not self.store.db.execute('SELECT 1 FROM turns WHERE turn_id=?', (rid,)).fetchone()
        await super().dispatch(request)
        if duplicate and missing and request['action'] == 'send':
            # The base journal stores no payload/outcome. Do not claim this was sent,
            # failed, free of billing, or even originally admitted as a Send.
            try:
                chat = self.store.chat(cid)
            except (ValueError, TypeError):
                return
            if (chat['provider'], chat['route'], chat['model']) != ('deepseek', 'api', 'deepseek-v4-pro'):
                return
            self.unknown_sends[cid] = self.latest_turn(cid)
            self.unknown_sends.move_to_end(cid)
            while len(self.unknown_sends) > self.MAX_UNKNOWN_CHATS:
                self.unknown_sends.popitem(last=False)

    def recovery_notice(self):
        cid = self.selected
        if not cid:
            return ''
        task = self.tasks.get(cid)
        if task is not None and not task.done():
            return ''
        latest = self.latest_turn(cid)
        if cid in self.unknown_sends:
            previous = self.unknown_sends[cid]
            # Finishing an older turn does not resolve a different admitted Send.
            # Compare identity, rather than clearing uncertainty on a status edit.
            if ((latest is None and previous is None) or
                    (latest is not None and previous is not None and latest[0] == previous[0])):
                return UNKNOWN
            del self.unknown_sends[cid]  # A later durable turn supersedes this warning.
        return INTERRUPTED if latest is not None and latest[1] == 'interrupted' else ''

    def write_ui(self):
        # Preserve base connection/error/status text and restore it even if writing fails.
        # Existing IPC2 notice encoding/bounds remain authoritative; no wire patching.
        previous = self.notice
        recovery = self.recovery_notice()
        try:
            if recovery:
                self.notice = previous + (' ' if previous else '') + recovery
            super().write_ui()
        finally:
            self.notice = previous
