"""Finite tile projections and predicates, serviced by public in-process game APIs."""
import base64
from typing import Annotated, Literal
from pydantic import Field, StrictBool, StrictInt, StrictStr, model_validator
from syx_live import StrictModel, _read_entities

TileCoordinate = Annotated[StrictInt, Field(ge=0, le=100000)]
TileKey = Annotated[StrictStr, Field(min_length=1, max_length=100)]


class TileSelection(StrictModel):
    tile_bounds: list[TileCoordinate] = Field(min_length=4, max_length=4)
    fields: list[Literal['terrain','floor','room','minerals','path']] = Field(
        default_factory=lambda:['terrain','floor','room'], min_length=1, max_length=5)
    terrain_id: TileKey | None = None
    floor_id: TileKey | None = None
    room_blueprint_id: TileKey | None = None
    mineral_resource_id: TileKey | None = None
    has_room: StrictBool | None = None
    throne_component_reachable: StrictBool | None = None
    cursor: Annotated[StrictInt,Field(ge=0,le=2**31-1)] = 0
    scan_limit: Annotated[StrictInt,Field(ge=1,le=4096)] = 4096
    limit: Annotated[StrictInt,Field(ge=1,le=100)] = 25
    expected_session_id: StrictStr | None = None

    @model_validator(mode='after')
    def bounds_and_fields(self):
        x1,y1,x2,y2=self.tile_bounds
        if x1>=x2 or y1>=y2:raise ValueError('Exclusive upper bounds [x1,y1,x2,y2] required')
        if self.cursor>(x2-x1)*(y2-y1):raise ValueError('Cursor exceeds rectangular area')
        if len(set(self.fields))!=len(self.fields):raise ValueError('Duplicate tile field')
        if self.has_room is False and self.room_blueprint_id is not None:
            raise ValueError('room_blueprint_id conflicts with has_room=false')
        return self

    def wire(self,request_id,session,expires):
        def key(value):return '' if value is None else base64.urlsafe_b64encode(value.encode()).decode().rstrip('=')
        def boolean(value):return '' if value is None else str(value).lower()
        values={'protocol':'1','request_id':request_id,'session':session,'expires':expires,
            'bounds':','.join(map(str,self.tile_bounds)),'cursor':self.cursor,'scan_limit':self.scan_limit,'limit':self.limit,
            'fields':','.join(self.fields),'terrain':key(self.terrain_id),'floor':key(self.floor_id),
            'room':key(self.room_blueprint_id),'mineral':key(self.mineral_resource_id),'has_room':boolean(self.has_room),
            'reachable':boolean(self.throne_component_reachable)}
        text=''.join(f'{k}={v}\n' for k,v in values.items())
        if len(text.encode())>8192:raise ValueError('Tile request exceeds 8 KiB')
        return text


def query_tiles(advisor,spec,*,timeout=8):
    selection=TileSelection.model_validate(spec)
    result=_read_entities(advisor,selection,timeout=timeout,channel='tile')
    data=result['data'];x1,y1,x2,y2=selection.tile_bounds
    if result.get('read_mode')!='tile_page' or data.get('bounds')!=selection.tile_bounds or data.get('cursor_kind')!='row_major_rectangle_offset':
        raise ValueError('Invalid tile response identity/bounds')
    count=data['scanned_tiles'];next_cursor=data.get('next_cursor');area=(x2-x1)*(y2-y1)
    end=selection.cursor+count
    if (count==0 and selection.cursor<area) or end>area or (next_cursor is not None and (type(next_cursor) is not int or next_cursor!=end or end>=area)) or (next_cursor is None and end!=area):
        raise ValueError('Invalid tile response cursor')
    errors=data.get('predicate_errors')
    if type(errors) is not int or not 0<=errors<=count or len(data['rows'])+errors>count:
        raise ValueError('Invalid tile predicate counts')
    seen=set()
    for row in data['rows']:
        if not isinstance(row,dict):raise ValueError('Invalid tile row')
        x,y=row.get('tile_x'),row.get('tile_y')
        if type(x) is not int or type(y) is not int or not x1<=x<x2 or not y1<=y<y2:
            raise ValueError('Tile coordinates exceed selection')
        position=(y-y1)*(x2-x1)+x-x1
        if not selection.cursor<=position<end or (x,y) in seen:raise ValueError('Invalid/duplicate tile position')
        seen.add((x,y))
    from pydantic_core import to_json
    if len(to_json(result,fallback=str,indent=2))>65536:
        raise ValueError('Tile tool text exceeds 64 KiB; reduce limit or fields')
    return result


TILE_QUERY_HELP={
    'tool':'query_live_tiles','selection':TileSelection.model_json_schema(),
    'boundary':'Fixed public terrain/floor/room/mineral/path getters in GAME.addAfterUpdate; detached DTOs only. No private fields, setters, rendering, input or arbitrary code.',
    'paging':'Rectangular tile bounds have exclusive upper limits. Cursor is the row-major offset within that rectangle, not a global tile index or matching-row count. Follow next_cursor even after empty pages. Each page is a separate mutable observation, not a retained entity capture.',
    'limits':'At most 4096 scanned tiles, 100 returned rows, 8 KiB request, 64 KiB local response, eight-second deadline. Narrow wide projections. Coordinates must fit the instantiated map; no city/battlefield or session mixing. POSIX transport.',
    'predicates':'All supplied filters combine with AND. Keys are exact observed identifiers; an unmatched identifier can return no rows. Predicate errors make matching absence/count unknown. No construction suitability is inferred.',
    'semantics':'Terrain flags are engine classifications. Floor degradation is the public getter factor, not an established lifetime. Room map records can be shared singletons: instance_room_id exists only for RoomInstance, map_record_id alone is not a unique building. Room-at-coordinate is not the UI-selected room. Minerals are deposit amount fields, not warehouse inventory, yield or exhaustion forecasts. Path costs/speed are raw availability factors; throne-component reachability includes adjacent components and is not a route for a particular person or army.',
    'scope':'Current instantiated city or battlefield tiles only; no full world map, fertility, private jobs, complete tile state or global worker transaction. Use returned session/tick/time/scene/UI context and get_game_api_support for evidence.'}

TILE_FIELD_DEFINITIONS={
    'coordinates':{'fields':['tile_x','tile_y'],'type':'integer','unit':'instantiated settlement tiles',
        'scope':'Each returned row identifies one coordinate in the explicit rectangle, not a UI cursor or world-map tile.'},
    'terrain':{'nullable':False,'source':'settlement/tilemap/terrain/Terrain.java',
        'fields':{'key':'installed terrain identifier','name':'installed display name','roof_flag':'public roofIs classification, including ceilings/openings',
            'massive_wall_flag':'public isMassiveWall classification'},'limits':'Flags are not construction eligibility or final visible terrain.'},
    'floor':{'nullable':True,'source':'settlement/tilemap/floor/Floors.java:764',
        'fields':{'key':'installed floor identifier','name':'installed display name','is_road':'floor definition road classification',
            'degradation_raw':'getter factor: stored degradation bits shifted once, divided by 7 (0..1)'},
        'limits':'Null means no floor reported. The getter factor does not establish remaining lifetime or a repair forecast.'},
    'room':{'nullable':True,'source':'settlement/room/main/RoomsMap.java; Room.java; RoomSingleton.java',
        'fields':{'map_record_id':'scene room-map record; can be shared by singleton rooms',
            'instance_room_id':'RoomInstance index, otherwise null; not a permanent ID',
            'blueprint_id':'installed room blueprint key','name':'public name for this coordinate',
            'anchor_tile_x':'public mX(x,y)','anchor_tile_y':'public mY(x,y)',
            'area_tiles':'public area(x,y), including singleton furniture bounding area'},
        'limits':'Not UI selection or actual occupants. Coordinate-aware singleton getters update reusable internal scratch caches; copy values immediately on game update thread. Do not equate map_record_id or bounding area with a unique building/usable floor area.'},
    'minerals':{'nullable':True,'source':'settlement/tilemap/ground/Minables.java:138',
        'fields':{'resource_id':'associated resource key','reference_id':'installed resource description ID',
            'amount_raw':'stored 6-bit tile amount (0..63)','amount_fraction':'amount_raw / 63',
            'richness_flag_raw':'stored one-bit richness value (0 or 1)'},
        'limits':'Null means no nonzero deposit reported. No warehouse count, extracted output, lifetime or economic multiplier inferred.'},
    'path':{'nullable':False,'source':'settlement/path/PATHING.java:172; AVAILABILITY.java',
        'fields':{'availability':'public availability enum name','available_to_stand_on':'engine flag',
            'tile_collide':'engine collision flag','player_cost_raw':'availability player factor; negative can mark solidity',
            'enemy_cost_raw':'availability enemy factor; may differ from player','movement_speed_raw':'availability movement factor',
            'throne_component_reachable':'tile or an orthogonal neighbor super-component connects to throne component'},
        'limits':'Published path components may await updates. No route, reachability for a particular agent, building suitability or visibility guaranteed.'},
    'availability':'Each projected group has available/data. available=true with data=null is a successful absence observation; available=false reports a getter failure. Predicate getter errors are counted separately.'}
TILE_QUERY_HELP['field_definitions']=TILE_FIELD_DEFINITIONS
