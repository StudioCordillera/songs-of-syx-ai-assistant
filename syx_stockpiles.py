"""Fixed public per-warehouse stored-bookkeeping pages; no gameplay commands."""
import base64
from typing import Annotated, Literal
from uuid import UUID
from pydantic import Field, StrictBool, StrictInt, StrictStr, model_validator
from pydantic_core import to_json
from syx_live import StrictModel, _read_entities

Counter = Literal['assigned_crates','stored_raw','capacity_raw','reserved_stored_raw','reserved_incoming_raw']
Projection = Literal['assigned_crates','stored_raw','capacity_raw','reserved_stored_raw','reserved_incoming_raw','reference_id']
Nonnegative = Annotated[StrictInt, Field(ge=0, le=2**31-1)]
Signed = Annotated[StrictInt, Field(ge=-(2**31), le=2**31-1)]


def canonical_uuid(value):
    if type(value) is not str or str(UUID(value)) != value:
        raise ValueError('Canonical UUID required')
    return value


class CounterFilter(StrictModel):
    field: Counter
    op: Literal['eq','ne','lt','lte','gt','gte']
    value: Signed

    def matches(self, value):
        return {'eq': value == self.value, 'ne': value != self.value, 'lt': value < self.value,
                'lte': value <= self.value, 'gt': value > self.value, 'gte': value >= self.value}[self.op]


class StockpileSelection(StrictModel):
    room_ids: list[Nonnegative] = Field(default_factory=list, max_length=100)
    resource_ids: list[Annotated[StrictStr, Field(min_length=1, max_length=100)]] = Field(min_length=1, max_length=100)
    fields: list[Projection] = Field(default_factory=lambda: ['assigned_crates','stored_raw','capacity_raw','reserved_stored_raw','reserved_incoming_raw'], min_length=1, max_length=6)
    filters: list[CounterFilter] = Field(default_factory=list, max_length=4)
    active: StrictBool | None = None
    cursor: Nonnegative = 0
    scan_limit: Annotated[StrictInt, Field(ge=1, le=4096)] = 4096
    limit: Annotated[StrictInt, Field(ge=1, le=100)] = 25
    expected_session_id: StrictStr | None = None

    @model_validator(mode='after')
    def validate_selection(self):
        for values in [self.room_ids, self.resource_ids, self.fields]:
            if len(values) != len(set(values)):
                raise ValueError('Duplicate stockpile selection item')
        for key in self.resource_ids:
            if len(key.encode('utf-16-le')) > 200:
                raise ValueError('Resource key exceeds 100 UTF-16 units')
            key.encode('utf-8')
        if self.room_ids and self.cursor > len(self.room_ids) * len(self.resource_ids):
            raise ValueError('Cursor exceeds explicit room/resource matrix')
        if self.expected_session_id is not None:
            canonical_uuid(self.expected_session_id)
        return self

    def wire(self, request_id, session, expires):
        canonical_uuid(request_id); canonical_uuid(session)
        if type(expires) is not int or not 10**12 <= expires < 10**13:
            raise ValueError('Invalid request deadline')
        resources = [base64.urlsafe_b64encode(k.encode()).decode().rstrip('=') for k in self.resource_ids]
        values = {'protocol':1, 'request_id':request_id, 'session':session, 'expires':expires,
                  'rooms':','.join(map(str,self.room_ids)), 'resources':','.join(resources), 'fields':','.join(self.fields),
                  'filters':','.join(f'{p.field}:{p.op}:{p.value}' for p in self.filters),
                  'active':'' if self.active is None else str(self.active).lower(), 'cursor':self.cursor,
                  'scan_limit':self.scan_limit, 'limit':self.limit}
        text = ''.join(f'{k}={v}\n' for k,v in values.items())
        if len(text.encode('ascii')) > 8192:
            raise ValueError('Stockpile request exceeds 8 KiB')
        return text


def _integer(value, minimum=0, maximum=2**31-1):
    return type(value) is int and minimum <= value <= maximum


def validate_page(result, selection):
    """After the shared transport has checked request/session/version/freshness correlation."""
    data = result['data']
    expected_source = 'explicit_room_ids' if selection.room_ids else 'current_warehouse_instance_slots'
    if (result.get('read_mode') != 'stockpile_page' or result.get('observer_phase') != 'GAME.addAfterUpdate' or
        result.get('scope') != 'instantiated_city_stockpile_bookkeeping' or result.get('coverage') != 'partial' or
        data.get('cursor_kind') != 'stockpile_room_resource_matrix' or data.get('room_source_kind') != expected_source or
        data.get('room_ids') != selection.room_ids or data.get('resource_ids') != selection.resource_ids or
        any(type(v) is not int for v in data.get('room_ids', []))):
        raise ValueError('Invalid stockpile response identity/scope')
    count = data.get('room_count_total'); registry = data.get('resource_registry_count')
    if (not _integer(count) or (selection.room_ids and count != len(selection.room_ids)) or
        not _integer(registry, len(selection.resource_ids), 1000) or type(data.get('resource_scan_limit')) is not int or data['resource_scan_limit'] != 1000):
        raise ValueError('Invalid stockpile registry/room count')
    area = count * len(selection.resource_ids)
    scanned = data['scanned_cells']; errors = data.get('cell_errors'); rows = data['rows']; cursor = data.get('next_cursor')
    if (area > 2**31-1 or not _integer(scanned,0,selection.scan_limit) or not _integer(errors,0,scanned) or
        len(rows) > selection.limit or len(rows)+errors > scanned):
        raise ValueError('Invalid stockpile scan/row/error bound')
    end = selection.cursor + scanned
    if (selection.cursor > area or end > area or (scanned == 0 and selection.cursor < area) or
        (cursor is None and end != area) or (cursor is not None and (not _integer(cursor) or cursor != end or end >= area)) or
        (end < area and scanned < selection.scan_limit and len(rows) < selection.limit)):
        raise ValueError('Invalid stockpile response cursor/early stop')
    if not selection.filters and selection.active is None and len(rows)+errors != scanned:
        raise ValueError('Missing unfiltered stockpile cells')
    if (not _integer(result.get('tick'),0,2**63-1) or not isinstance(result.get('scene'),dict) or
        not isinstance(result.get('ui_context'),dict) or not isinstance(result.get('consistency'),str) or not result['consistency']):
        raise ValueError('Invalid stockpile observation context')
    blueprint = data.get('stockpile_blueprint_id')
    if type(blueprint) is not str or not blueprint:
        raise ValueError('Invalid stockpile blueprint identity')
    mandatory = {'matrix_position','room_id','resource_id','room_blueprint_id','anchor_tile_x','anchor_tile_y','room_active'}
    last = selection.cursor-1; slots = {}; room_slots = {}
    for row in rows:
        if not isinstance(row,dict) or set(row) != mandatory | set(selection.fields):
            raise ValueError('Invalid stockpile projection')
        position = row['matrix_position']; rid = row['room_id']
        if (not _integer(position) or not max(selection.cursor,last+1) <= position < end or not _integer(rid) or
            row['resource_id'] != selection.resource_ids[position % len(selection.resource_ids)] or
            row['room_blueprint_id'] != blueprint or type(row['room_active']) is not bool or
            not _integer(row['anchor_tile_x']) or not _integer(row['anchor_tile_y'])):
            raise ValueError('Invalid stockpile row identities/order')
        last = position; slot = position // len(selection.resource_ids)
        if selection.room_ids and rid != selection.room_ids[slot]:
            raise ValueError('Stockpile row does not match explicit room slot')
        identity = (rid, row['room_blueprint_id'], row['anchor_tile_x'], row['anchor_tile_y'], row['room_active'])
        if (slot in slots and slots[slot] != identity) or (rid in room_slots and room_slots[rid] != slot):
            raise ValueError('Inconsistent stockpile room slot identity')
        slots[slot] = identity; room_slots[rid] = slot
        if selection.active is not None and row['room_active'] != selection.active:
            raise ValueError('Stockpile row violates active predicate')
        for field in selection.fields:
            value = row[field]
            if field == 'reference_id':
                if value != 'resource:' + row['resource_id']:
                    raise ValueError('Invalid stockpile resource reference')
            elif not _integer(value,-(2**31),2**31-1):
                raise ValueError('Invalid stockpile raw signed counter')
        for predicate in selection.filters:
            if predicate.field in row and not predicate.matches(row[predicate.field]):
                raise ValueError('Stockpile row violates counter predicate')
    if len(to_json(result,indent=2)) > 65536:
        raise ValueError('Stockpile tool text exceeds 64 KiB; narrow fields/limit')
    return result


def query_stockpiles(advisor, spec, *, timeout=8):
    selection = StockpileSelection.model_validate(spec)
    return validate_page(_read_entities(advisor,selection,timeout=timeout,channel='stockpile'),selection)


STOCKPILE_QUERY_HELP = {
    'tool':'query_live_stockpiles', 'selection':StockpileSelection.model_json_schema(),
    'boundary':'Fixed source-verified public per-warehouse stored tallies in GAME.addAfterUpdate. No crate scratch handle, refresh, gameplay command, private reflection or arbitrary invocation. Not a documented stable official contract.',
    'identities':'Exact installed resource keys; explicit current room IDs or empty room_ids for current warehouse instance-slot discovery. Unknown/non-warehouse identities refuse, never zero. Room IDs can be reused: inspect blueprint, anchors, session and observation time. Not UI-selected rooms or permanent world identities.',
    'paging':'Cursor indexes warehouse-slot x resource matrix, including filtered/error cells. Follow next_cursor even after empty pages. Implicit slots can reorder and explicit IDs can be reused between callbacks. Each page has separate tick/time/scene/UI; no retained or global transaction.',
    'limits':'100 explicit rooms/100 resource keys, 1000 resource bindings, 4096 scanned cells/100 matching rows per page; four AND counter predicates plus active filter. 8 KiB request/64 KiB response, eight-second deadline. Shared POSIX request lock serializes entity/tile/regional/stockpile reads. Cell errors qualify missing matches.',
    'semantics':'Resource-specific assigned crates, stored items (including reserved stored items), assigned item capacity, reserved stored items and reserved incoming capacity. Preserve zero capacity, inactive stored bookkeeping and signed raw values. Not free-to-use stock, all settlement inventory, actual deliveries, physical fullness or exact tally age. Available only for completed instantiated campaign cities, including underlying city while another view is open.',
    'provenance':['STOCKPILE_BOUNDARY_REVIEW.json','STOCKPILE_BOOKKEEPING.md','STOCKPILE_LIVE_CANDIDATE.md'],
}
