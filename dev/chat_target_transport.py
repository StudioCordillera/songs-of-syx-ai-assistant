"""Developer-only async target evidence over one caller-owned MCP session.

No new tools, process spawn, reconnect, automatic capture, enqueue or game writes.
The caller owns ClientSession lifetime; instantiate anew after server replacement.
"""
import asyncio
import json

from mcp import ClientSession

from dev.chat_target_candidate import (
    DraftEvidence, bounded, canonical, observed_page, page_arguments, uuid, active_view,
)

READ_TOOLS = {'entity': 'read_entity_capture', 'tile': 'read_tile_capture',
              'regional_output': 'read_regional_output_capture'}
TOOL_SET = frozenset({'game_status', *READ_TOOLS.values()})
OPERATION_SECONDS = 5


class McpTargetDrafts:
    """Serialize draft operations; immutable original pages survive transport errors.

    Preview is detached historical data, not a liveness probe. Each async operation
    has one whole-operation deadline; no paid call or hidden retry occurs.
    """
    def __init__(self, session):
        if not isinstance(session, ClientSession):
            raise ValueError('An initialized caller-owned MCP ClientSession is required')
        self._session = session
        self._draft = DraftEvidence()
        self._lock = asyncio.Lock()
        self._ready = False

    async def _admit(self):
        if self._ready:
            return
        try:
            listing = await self._session.list_tools()
        except Exception as error:
            raise ValueError('Capture connection unavailable; draft retained, no message sent') from error
        selected = {t.name for t in listing.tools if t.name in TOOL_SET and t.annotations
                    and t.annotations.read_only_hint is True and t.annotations.idempotent_hint is True}
        if selected != TOOL_SET:
            raise ValueError('Required read-only idempotent capture tools unavailable')
        self._ready = True

    async def _call(self, name, arguments):
        if name not in TOOL_SET:
            raise ValueError('Unsupported target reader')
        try:
            result = await self._session.call_tool(name, arguments)
        except Exception as error:
            raise ValueError('Capture connection unavailable; draft retained, no message sent') from error
        if result.is_error:
            raise ValueError('Target observation unavailable; token may have expired or game context changed. Remove or pick again.')
        if len(result.content) > 1 or any(block.type != 'text' for block in result.content):
            raise ValueError('Expected at most one JSON text content block')
        value = result.structured_content
        text = result.content[0].text if result.content else None
        byte_count = len(text.encode('utf-8')) if text is not None else 0
        if value is not None:
            byte_count += len(canonical(value))
        if byte_count > 65536:
            raise ValueError('Capture response exceeds 64 KiB')
        if value is None:
            if text is None:
                raise ValueError('Expected one JSON capture response')
            try:
                value = json.loads(text)
            except RecursionError as error:
                raise ValueError('Excessively nested capture response; narrow fields') from error
        elif text is not None:
            try:
                duplicate = json.loads(text)
            except RecursionError as error:
                raise ValueError('Excessively nested capture response; narrow fields') from error
            if canonical(duplicate) != canonical(value):
                raise ValueError('Conflicting structured and text capture responses')
        if not isinstance(value, dict):
            raise ValueError('Expected a bounded JSON object capture response')
        return value

    async def _status(self):
        state = await self._call('game_status', {})
        if state.get('fresh') is not True or state.get('live') is not True:
            raise ValueError('Fresh loaded non-demo game observation required')
        uuid(state.get('session_id')); active_view(state.get('scene'))
        if not isinstance(state.get('game_version'), str):
            raise ValueError('Known game version required')
        return state

    @staticmethod
    def _origin(meta, state):
        if (meta['session_id'], meta['game_version']) != (state['session_id'], state['game_version']):
            raise ValueError('Capture runtime/version changed; pick a new target')
        if canonical(meta['scene']) != canonical(state['scene']):
            raise ValueError('Capture scene changed; pick a new target')

    async def _page(self, kind, capture_id, offset, limit, state):
        page_arguments(kind, capture_id, offset, limit)
        page = await self._call(READ_TOOLS[kind], {'capture_id': capture_id,
                'offset': offset, 'limit': limit, 'include_ui_context': False})
        return observed_page(kind, capture_id, offset, limit, page, state)

    def preview(self, chat_id):
        return self._draft.preview(chat_id)

    async def remove(self, chat_id, attachment_id):
        try:
            async with asyncio.timeout(OPERATION_SECONDS), self._lock:
                self._draft.remove(chat_id, attachment_id)
        except TimeoutError as error:
            raise ValueError('Target removal timed out; draft retained') from error

    async def stage(self, chat_id, kind, capture_id, *, offset=0, limit=1):
        uuid(chat_id); page_arguments(kind, capture_id, offset, limit)
        try:
            async with asyncio.timeout(OPERATION_SECONDS), self._lock:
                self._draft.check_stage(chat_id)
                await self._admit()
                state = await self._status()
                page, remaining = await self._page(kind, capture_id, offset, limit, state)
                self._origin(state, await self._status())
                return self._draft.stage_observation(chat_id, page, remaining)
        except TimeoutError as error:
            raise ValueError('Target preparation timed out; draft retained, no message sent') from error

    async def prepare(self, chat_id):
        uuid(chat_id)
        try:
            async with asyncio.timeout(OPERATION_SECONDS), self._lock:
                await self._admit()
                state = await self._status()
                items = self._draft.preview(chat_id)
                for item in items:
                    meta = item['capture']
                    self._origin(meta, state)
                    page, _ = await self._page(item['kind'], meta['capture_id'], item['offset'], item['limit'], state)
                    self._draft.verify_observation(chat_id, item['attachment_id'], page)
                self._origin(state, await self._status())
                return json.loads(bounded(self._draft._envelope(chat_id, items)))
        except TimeoutError as error:
            raise ValueError('Target preparation timed out; draft retained, no message sent') from error
