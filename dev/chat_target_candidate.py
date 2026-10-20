"""Developer-only next-message capture attachments; no UI, dispatch or game calls.

Explicit capture pages are observations, never permanent object handles or actions.
Only existing fixed read methods are used. The production player does not import
this module. Drafts are in memory and must not be treated as a durable send queue.
"""
from datetime import datetime
from hashlib import sha256
import json
from uuid import UUID, uuid4

from syx_capture import EntityCaptures, TileCaptures, RegionalCaptures

MAX_CHATS = 100
MAX_ATTACHMENTS = 8
MAX_BYTES = 32768
KINDS = ('entity', 'tile', 'regional_output')
NOTICE = ('Attached rows are retained historical observations, not current values, '
          'UI selections, permanent identities, executable targets or a shared '
          'transaction. Different captures retain separate ticks and times.')


def canonical(value):
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False,
                          sort_keys=True, separators=(',', ':')).encode('utf-8')
    except (ValueError, RecursionError) as error:
        raise ValueError('Attachment contains non-finite or excessively nested values; narrow projected fields or choose another capture') from error


def uuid(value):
    if type(value) is not str:
        raise ValueError('Canonical UUID required')
    try:
        if str(UUID(value)) != value:
            raise ValueError('Canonical UUID required')
    except (ValueError, AttributeError) as error:
        raise ValueError('Canonical UUID required') from error
    return value


def active_view(value):
    view = value.get('active_view') if isinstance(value, dict) else None
    if type(view) is not str or not view.strip() or view.casefold() in {'unknown', 'unavailable', 'none', 'other'}:
        raise ValueError('Known current/captured scene required')
    return view


def bounded(value):
    raw = canonical(value)
    if len(raw) > MAX_BYTES:
        raise ValueError('Attachments exceed 32 KiB; narrow the selected pages')
    return raw


def page_arguments(kind, capture_id, offset, limit):
    if kind not in KINDS:
        raise ValueError('Unsupported target kind; use an explicit capture picker')
    uuid(capture_id)
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('Explicit offset >=0 and limit 1..100 required')


def validate_page_shape(kind, capture_id, offset, limit, page):
    """Refuse mismatched remote pages before retaining any evidence."""
    page_arguments(kind, capture_id, offset, limit)
    if not isinstance(page, dict) or not isinstance(page.get('capture'), dict):
        raise ValueError('Malformed capture page')
    meta = page['capture'];rows = page.get('rows');total = meta.get('row_count')
    if (meta.get('capture_id') != capture_id or type(page.get('offset')) is not int
            or page['offset'] != offset or type(total) is not int
            or not 0 <= offset <= total <= (100 if kind == 'tile' else 2000)
            or not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows)
            or len(rows) != min(limit, max(0, total-offset))):
        raise ValueError('Mismatched capture page identity, offset or rows')
    expected_next = offset + limit if offset + limit < total else None
    if (page.get('next_offset') != expected_next or ('next_offset' not in page)
            or (expected_next is not None and type(page['next_offset']) is not int)):
        raise ValueError('Mismatched capture page continuation')
    if kind != 'entity' and (meta.get('capture_kind') != kind or meta.get('selection_complete') is not True):
        raise ValueError('Mismatched capture kind or incomplete selection')
    if not isinstance(page.get('current_state'), dict):
        raise ValueError('Capture page current state required')
    for state in (meta, page['current_state']):
        uuid(state.get('session_id'))
        if not isinstance(state.get('game_version'), str):
            raise ValueError('Capture version required')
    current = page['current_state']
    if current.get('live') is not True or current.get('fresh') is not True:
        raise ValueError('Fresh capture page current state required')
    remaining = meta.get('retention_remaining_seconds')
    if type(remaining) not in (int, float) or not 0 <= remaining <= 120:
        raise ValueError('Bounded capture retention hint required')
    if type(meta.get('tick')) is not int or meta['tick'] < 0 or not isinstance(meta.get('selection'), dict):
        raise ValueError('Capture tick and selection provenance required')
    for key in ('captured_at','scope','consistency','coverage','warning'):
        if not isinstance(meta.get(key), str) or not meta[key]:
            raise ValueError('Missing capture provenance: '+key)
    try:
        captured = datetime.fromisoformat(meta['captured_at'].replace('Z', '+00:00'))
        if captured.utcoffset() is None:
            raise ValueError('Timezone required')
    except ValueError as error:
        raise ValueError('Capture timestamp with timezone required') from error


def observed_page(kind, capture_id, offset, limit, page, state):
    validate_page_shape(kind, capture_id, offset, limit, page)
    meta, current = page['capture'], page['current_state']
    for observed in (meta, current):
        if (observed['session_id'], observed['game_version']) != (state['session_id'], state['game_version']):
            raise ValueError('Capture runtime/version changed; pick a new target')
        active_view(observed.get('scene'))
        if canonical(observed['scene']) != canonical(state['scene']):
            raise ValueError('Capture scene changed; pick a new target')
    if not page['rows']:
        raise ValueError('No observed rows in this page; nothing to attach')
    # Dynamic ages/current status are not original observation provenance.
    provenance = {key: value for key, value in meta.items()
                  if key not in ('captured_age_seconds', 'retention_remaining_seconds')}
    return ({'kind': kind, 'capture': provenance, 'offset': offset,
             'limit': limit, 'rows': page['rows'], 'next_offset': page['next_offset']},
            meta['retention_remaining_seconds'])



class DraftEvidence:
    """Detached mutation core shared by local and async MCP adapters."""
    def __init__(self):
        self._drafts = {}

    def check_stage(self, chat_id):
        uuid(chat_id)
        existing = self._drafts.get(chat_id, {})
        if len(existing) >= MAX_ATTACHMENTS:
            raise ValueError('At most eight attachments per chat')
        if chat_id not in self._drafts and len(self._drafts) >= MAX_CHATS:
            raise ValueError('At most 100 draft chats; remove old targets explicitly')

    def stage_observation(self, chat_id, page, remaining):
        self.check_stage(chat_id)
        kind, capture_id, offset = page["kind"], page["capture"]["capture_id"], page["offset"]
        raw = bounded(page)
        if any(item['raw'] == raw for item in self._drafts.get(chat_id, {}).values()):
            raise ValueError('This exact capture page is already attached')
        for previous in self.preview(chat_id):
            if previous['kind'] == kind and previous['capture']['capture_id'] == capture_id:
                if max(previous['offset'], offset) < min(previous['offset'] + len(previous['rows']), offset + len(page['rows'])):
                    raise ValueError('Capture pages overlap; select non-overlapping rows')
        attachment_id = str(uuid4())
        item = {'attachment_id': attachment_id, **page, 'observation_sha256': sha256(raw).hexdigest(),
                'retention_hint': {'remaining_seconds_at_stage': remaining,
                    'notice': 'Estimate at staging only, not revalidated liveness. Eviction or server restart can expire this target earlier; remove or pick again.'}}
        # Validate the whole outgoing envelope before mutating any draft.
        bounded(self._envelope(chat_id, [*self.preview(chat_id), item]))
        stored = {'raw': raw, 'item': bounded(item)}
        self._drafts.setdefault(chat_id, {})[attachment_id] = stored
        return json.loads(stored['item'])

    def verify_observation(self, chat_id, attachment_id, page):
        """Compare normalized original evidence, excluding dynamic age metadata."""
        uuid(chat_id); uuid(attachment_id)
        stored = self._drafts.get(chat_id, {}).get(attachment_id)
        if stored is None or bounded(page) != stored['raw']:
            raise ValueError('Captured evidence changed or removed; pick a new target')

    def preview(self, chat_id):
        uuid(chat_id)
        # Detached copies; stale observations remain removable/historical here.
        return [json.loads(item['item']) for item in self._drafts.get(chat_id, {}).values()]

    def remove(self, chat_id, attachment_id):
        uuid(chat_id); uuid(attachment_id)
        draft = self._drafts.get(chat_id)
        if draft is None or attachment_id not in draft:
            raise ValueError('Attachment does not belong to this chat')
        del draft[attachment_id]
        if not draft:
            del self._drafts[chat_id]

    @staticmethod
    def _envelope(chat_id, items):
        return {'schema': 'syx-target-preview-1', 'chat_id': chat_id,
                'notice': NOTICE, 'has_attachments': bool(items), 'attachments': items}



class TargetDrafts(DraftEvidence):
    """Own composer evidence pinned to a chat/runtime and rechecked before send.

    The caller must supply the pools owned by one MCP server and serialize draft
    mutations. This candidate does not bridge independent MCP processes or add
    arbitrary readers. All-or-nothing prepare leaves drafts intact on failure.
    """
    def __init__(self, entities, tiles, regions):
        if (type(entities) is not EntityCaptures or type(tiles) is not TileCaptures
                or type(regions) is not RegionalCaptures):
            raise ValueError('The three fixed production capture pools are required')
        if entities.advisor is not tiles.advisor or entities.advisor is not regions.advisor:
            raise ValueError('Capture pools must belong to the same advisor')
        self.pools = dict(zip(KINDS, (entities, tiles, regions)))
        self.advisor = entities.advisor
        super().__init__()

    def _status(self):
        state = self.advisor.status()
        if state.get('live') is not True or state.get('fresh') is not True:
            raise ValueError('Fresh loaded non-demo game observation required')
        uuid(state.get('session_id'))
        active_view(state.get('scene'))
        return state

    def _page(self, kind, capture_id, offset, limit, state):
        if kind not in KINDS:
            raise ValueError('Unsupported target kind; use an explicit capture picker')
        uuid(capture_id)
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('Explicit offset >=0 and limit 1..100 required')
        page = self.pools[kind].read(capture_id, offset, limit)
        return observed_page(kind, capture_id, offset, limit, page, state)

    def stage(self, chat_id, kind, capture_id, *, offset=0, limit=1):
        self.check_stage(chat_id)
        state = self._status()
        page, remaining = self._page(kind, capture_id, offset, limit, state)
        return self.stage_observation(chat_id, page, remaining)

    def prepare(self, chat_id):
        """Revalidate all pages, returning evidence only; never enqueue or clear.

        A future coordinator must revalidate again after async waits, preserve
        turn provenance, and clear only exact accepted draft IDs on queue ack.
        """
        uuid(chat_id)
        state = self._status()
        items = self.preview(chat_id)
        for item in items:
            meta = item['capture']
            if (meta['session_id'], meta['game_version']) != (state['session_id'], state['game_version']):
                raise ValueError('Capture runtime/version changed; pick a new target')
            if canonical(meta['scene']) != canonical(state['scene']):
                raise ValueError('Capture scene changed; pick a new target')
            page, _ = self._page(item['kind'], item['capture']['capture_id'],
                              item['offset'], item['limit'], state)
            self.verify_observation(chat_id, item['attachment_id'], page)
        # Catch observed transitions while multiple independent pools were read.
        final = self._status()
        if (final['session_id'], final['game_version'], canonical(final['scene'])) != (
                state['session_id'], state['game_version'], canonical(state['scene'])):
            raise ValueError('Runtime/version/scene changed while preparing targets')
        return json.loads(bounded(self._envelope(chat_id, items)))
