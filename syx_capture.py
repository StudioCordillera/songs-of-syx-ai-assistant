"""Retain bounded, encoded entity observations; paging never rereads game objects."""
from collections import OrderedDict
from datetime import datetime, timezone
import json
import threading
import time
from uuid import UUID, uuid4
from pydantic_core import to_json

from syx_live import EntityCaptureSelection, capture_entities

PAYLOAD_CAP = 2 * 1024 * 1024
RETENTION_SECONDS = 120
MAX_CAPTURES = 3


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


class EntityCaptures:
    """Server-local tokens and immutable encoded payloads; no game references or persisted leases."""
    def __init__(self, advisor):
        self.advisor = advisor
        self._captures = OrderedDict()
        self._lock = threading.RLock()

    def _prune(self, now):
        for token, (created, _) in list(self._captures.items()):
            if now - created >= RETENTION_SECONDS:
                del self._captures[token]

    def _current(self, payload):
        snapshot = self.advisor.snapshot()
        if snapshot.session_id != payload['session_id'] or snapshot.game_version != payload['game_version']:
            raise ValueError('Capture session/version changed; create a new capture')
        status = self.advisor.status(snapshot)
        if not status['live']:
            raise ValueError('Capture reads require a fresh loaded non-demo game observation')
        return status

    def _metadata(self, token, created, payload, now):
        captured = datetime.fromisoformat(payload['captured_at'].replace('Z', '+00:00'))
        return {'capture_id': token, 'session_id': payload['session_id'], 'game_version': payload['game_version'],
                'tick': payload['tick'], 'observer_phase': payload.get('observer_phase'), 'captured_at': payload['captured_at'],
                'captured_age_seconds': round((datetime.now(timezone.utc) - captured).total_seconds(), 2),
                'retention_remaining_seconds': round(max(0, RETENTION_SECONDS - (now - created)), 2),
                'row_count': len(payload['data']['rows']), 'scene': payload.get('scene'),
                'selection': payload['selection'], 'scope': payload.get('scope'),
                'coverage': 'partial', 'consistency': payload['consistency'],
                'warning': 'Pages retain the original observation, not current values. Other live queries and captures are different observations. No global worker-thread transaction, full game-state schema or permanent entity IDs are established.'}

    def create(self, spec):
        selection = EntityCaptureSelection.model_validate(spec)
        payload = capture_entities(self.advisor, spec)
        rows = payload['data']['rows']
        if 'next_cursor' not in payload['data'] or payload['data']['next_cursor'] is not None:
            raise ValueError('Incomplete capture; no selection retained')
        if not all(isinstance(row, dict) for row in rows):
            raise ValueError('Capture rows must be objects')
        ids = [row.get('id') for row in rows]
        if any(type(entity_id) is not int or not -(2**31) <= entity_id < 2**31 for entity_id in ids) or len(set(ids)) != len(ids):
            raise ValueError('Capture lacks unique integer entity identities')
        payload['selection'] = selection.model_dump(mode='json', by_alias=True)
        raw = encoded(payload)
        if len(raw) > PAYLOAD_CAP:
            raise ValueError('Capture exceeds 2 MiB; select fewer fields, stats or entities')
        current = self._current(payload)
        token = str(uuid4())
        now = time.monotonic()
        result = {'capture': self._metadata(token, now, payload, now), 'current_state': current,
                  'next_step': 'Call read_entity_capture with capture_id and row offset; no game reads occur while paging.'}
        if len(to_json(result, fallback=str, indent=2)) > 65536:
            raise ValueError('Capture metadata exceeds 64 KiB; narrow selection')
        with self._lock:
            self._prune(now)
            while len(self._captures) >= MAX_CAPTURES:
                self._captures.popitem(last=False)
            self._captures[token] = (now, raw)
        return result

    def read(self, capture_id, offset=0, limit=25, include_ui_context=False):
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 100 or type(include_ui_context) is not bool:
            raise ValueError('Offset >=0, limit 1..100 and a boolean include_ui_context are required')
        try:
            if str(UUID(capture_id)) != capture_id:
                raise ValueError()
        except (ValueError, TypeError, AttributeError) as error:
            raise ValueError('Capture ID must be a canonical UUID') from error
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            if capture_id not in self._captures:
                raise ValueError('Capture missing, expired or evicted; create a new capture')
            created, raw = self._captures[capture_id]
            # Decode a fresh tree for each response, preventing callers from mutating retained data.
            payload = json.loads(raw)
            try:
                current = self._current(payload)
            except ValueError:
                snapshot = self.advisor.snapshot()
                if snapshot.session_id != payload['session_id'] or snapshot.game_version != payload['game_version']:
                    del self._captures[capture_id]
                raise
        rows = payload['data']['rows']
        if offset > len(rows):
            raise ValueError('Offset exceeds captured row count')
        result = {'capture': self._metadata(capture_id, created, payload, now), 'current_state': current,
                  'rows': rows[offset:offset + limit], 'offset': offset,
                  'next_offset': offset + limit if offset + limit < len(rows) else None}
        if include_ui_context:
            result['captured_ui_context'] = payload.get('ui_context')
        if len(to_json(result, fallback=str, indent=2)) > 65536:
            raise ValueError('Capture page exceeds 64 KiB; reduce limit or omit UI context')
        return result


CAPTURE_HELP = {
    'create_tool': 'capture_live_entities', 'read_tool': 'read_entity_capture',
    'selection': EntityCaptureSelection.model_json_schema(),
    'semantics': 'Copies the entire matching bounded selection during one game after-update callback. Then pages encoded DTOs retained in this MCP server; it never returns an incomplete selection as complete. This is not a global simulation/battle-worker transaction.',
    'limits': 'At most 2000 rows (max_rows), 100000 scanned slots (scan_limit), 4000 projected stat cells and a 2 MiB local payload. Row/scan/predicate/byte failures retain nothing. Three captures per server, 120 seconds each, oldest evicted when full. Tokens do not survive server restart and are not shared between server processes.',
    'paging': 'Creation returns metadata only. read_entity_capture uses offset/limit over retained rows, at most 100 rows and 64 KiB per response; reduce limit for wide projections. include_ui_context returns the original captured UI context, not current UI. Pages keep original tick/time/session. A fresh loaded same-session/version game observation is required; expired, missing or changed-session captures fail explicitly.',
    'boundary': 'Fixed public entity projections/filters only, id required. Existing live cursor reads remain separate mutable observations. Capture queries do not freeze or pause the game and do not add native/OS control. Requires paired updated mod and MCP builds.',
}
