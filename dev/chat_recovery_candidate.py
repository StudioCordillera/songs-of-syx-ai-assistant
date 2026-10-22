"""Developer-only, plain recovery notices beside the unchanged simple coordinator.

No action resubmission, new history schema, inference, receipt or game API is added.
Construction requires caller-owned disposable state/history under runtime/.
"""
from collections import OrderedDict
from syx_chat_service import Coordinator
from dev.blueprint_mcp_candidate import isolated_state_dir

INTERRUPTED = 'Earlier reply interrupted; no automatic retry.'
UNKNOWN = 'Earlier Send outcome unknown; no automatic retry.'


class RecoveryCoordinator(Coordinator):
    MAX_UNKNOWN_CHATS = 100

    def __init__(self, store, mcp, state_dir, api_key):
        directory = isolated_state_dir(str(state_dir))
        isolated_state_dir(str(store.directory))
        super().__init__(store, mcp, directory, api_key, simple=True)
        # Reconstructed only from an observed duplicate Send, never guessed from an ack.
        self.unknown_sends = OrderedDict()

    def latest_turn(self, chat):
        return self.store.db.execute(
            'SELECT turn_id,status FROM turns WHERE chat_id=? ORDER BY rowid DESC LIMIT 1',
            (chat,)).fetchone()

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
            if latest == self.unknown_sends[cid]:
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
                self.notice = previous + ' ' + recovery
            super().write_ui()
        finally:
            self.notice = previous
