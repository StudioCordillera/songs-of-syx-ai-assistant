"""Bounded read requests serviced by the mod's update thread, not process inspection."""
from __future__ import annotations
import base64
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
from typing import Annotated, Literal, ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, model_validator

Int32 = Annotated[StrictInt, Field(ge=-(2**31), le=2**31-1)]
StatId = Annotated[StrictInt, Field(ge=0, le=100000)]
OutputField = Literal['id','entity_type','tile_x','tile_y','race_id','class_id','humanoid_type_id','stats','relationships']

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class StatFilter(StrictModel):
    stat_id: StatId
    op: Literal['eq','ne','lt','lte','gt','gte']
    value: Int32

class EntitySelection(StrictModel):
    STAT_CELL_LIMIT: ClassVar[int] = 100
    entity_ids: list[Int32] = Field(default_factory=list, max_length=100)
    race_id: StrictStr | None = Field(default=None,min_length=1,max_length=100)
    class_id: StrictStr | None = Field(default=None,min_length=1,max_length=100)
    humanoid_type_id: StrictStr | None = Field(default=None,min_length=1,max_length=100)
    tile_bounds: list[Annotated[StrictInt,Field(ge=0,le=100000)]] | None = Field(default=None,min_length=4,max_length=4)
    stat_filters: list[StatFilter] = Field(default_factory=list,max_length=4)
    fields: list[OutputField] = Field(default_factory=lambda:['id','entity_type','tile_x','tile_y','race_id'],min_length=1,max_length=9)
    stat_ids: list[StatId] = Field(default_factory=list,max_length=20)
    cursor: Annotated[StrictInt,Field(ge=0,le=2**31-1)] = 0
    scan_limit: Annotated[StrictInt,Field(ge=1,le=10000)] = 10000
    limit: Annotated[StrictInt,Field(ge=1,le=100)] = 25
    expected_session_id: StrictStr | None = None

    @model_validator(mode='after')
    def validate_selection(self):
        for values in (self.entity_ids,self.fields,self.stat_ids):
            if len(values)!=len(set(values)):raise ValueError('Duplicate selection item')
        if self.tile_bounds and (self.tile_bounds[0]>=self.tile_bounds[2] or self.tile_bounds[1]>=self.tile_bounds[3]):
            raise ValueError('Tile bounds are [x1,y1,x2,y2], with exclusive upper bounds')
        if 'stats' in self.fields:
            if not self.stat_ids or len(self.stat_ids)*self.limit>self.STAT_CELL_LIMIT:
                raise ValueError(f'Select 1..20 stat IDs and at most {self.STAT_CELL_LIMIT} returned stat cells (row bound × stat_ids)')
        elif self.stat_ids:raise ValueError('stat_ids require stats in fields')
        return self

    def wire(self,request_id:str,session:str,expires:int)->str:
        def encoded(value):return '' if value is None else base64.urlsafe_b64encode(value.encode()).decode().rstrip('=')
        values={'protocol':'1','request_id':request_id,'session':session,'expires':str(expires),
            'cursor':str(self.cursor),'scan_limit':str(self.scan_limit),'limit':str(self.limit),
            'ids':','.join(map(str,self.entity_ids)),'race':encoded(self.race_id),'class':encoded(self.class_id),
            'type':encoded(self.humanoid_type_id),'bounds':','.join(map(str,self.tile_bounds or [])),
            'fields':','.join(self.fields),'stats':','.join(map(str,self.stat_ids)),
            'filters':','.join(f'{f.stat_id}:{f.op}:{f.value}' for f in self.stat_filters)}
        text=''.join(f'{key}={value}\n' for key,value in values.items())
        if len(text.encode())>8192:raise ValueError('Read request exceeds 8 KiB')
        return text

class EntityCaptureSelection(EntitySelection):
    STAT_CELL_LIMIT: ClassVar[int] = 4000
    limit: Annotated[StrictInt,Field(ge=1,le=2000)] = Field(default=2000,alias='max_rows')
    scan_limit: Annotated[StrictInt,Field(ge=1,le=100000)] = 100000
    cursor: Annotated[StrictInt,Field(ge=0,le=0)] = 0

    @model_validator(mode='after')
    def validate_capture(self):
        if 'id' not in self.fields:raise ValueError('Capture requires id in fields')
        return self

    def wire(self,request_id:str,session:str,expires:int)->str:
        return super().wire(request_id,session,expires).replace('protocol=1\n','protocol=2\n',1)

@contextmanager
def request_lock(directory:Path,deadline:float):
    # flock is released by the OS on process exit, so failed clients leave no stale lease.
    try:import fcntl
    except ImportError as exc:raise ValueError('On-demand transport currently requires a POSIX MCP host') from exc
    path=directory/'entity-query.lock'
    if path.is_symlink():raise ValueError('Refusing symlink request lock')
    fd=os.open(path,os.O_CREAT|os.O_RDWR|getattr(os,'O_NOFOLLOW',0),0o600)
    acquired=False
    try:
        while not acquired:
            try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);acquired=True
            except BlockingIOError:
                if time.monotonic()>=deadline:raise ValueError('Another read request is busy; retry')
                time.sleep(.05)
        yield
    finally:
        if acquired:fcntl.flock(fd,fcntl.LOCK_UN)
        os.close(fd)

def query_entities(advisor,spec:dict,*,timeout:float=8)->dict:
    return _read_entities(advisor,EntitySelection.model_validate(spec),timeout=timeout)

def capture_entities(advisor,spec:dict,*,timeout:float=8)->dict:
    return _read_entities(advisor,EntityCaptureSelection.model_validate(spec),timeout=timeout,capture=True)

def _read_entities(advisor,selection,*,timeout:float,capture=False)->dict:
    from syx_mcp import load_json
    snapshot=advisor.snapshot();status=advisor.status(snapshot)
    if not status['live']:raise ValueError('On-demand reads require a fresh loaded non-demo game')
    if selection.expected_session_id is not None and selection.expected_session_id!=snapshot.session_id:
        raise ValueError('Session changed; rediscover game state')
    try:
        if str(UUID(snapshot.session_id))!=snapshot.session_id:raise ValueError()
    except ValueError as exc:raise ValueError('Exporter session is not a canonical UUID') from exc
    directory=advisor.snapshot_path.parent
    deadline=time.monotonic()+timeout
    request_id=str(uuid4())
    with request_lock(directory,deadline):
        remaining=deadline-time.monotonic()
        if remaining<.5:raise ValueError('Read request timed out waiting for transport')
        request=directory/'entity-request.txt'
        response=directory/'entity-response.json'
        if request.is_symlink() or response.is_symlink():raise ValueError('Refusing symlink read transport')
        tmp=directory/f'entity-request-{request_id}.tmp'
        try:
            with tmp.open('x',encoding='utf-8') as f:
                f.write(selection.wire(request_id,snapshot.session_id,int(time.time()*1000+remaining*1000)))
            os.replace(tmp,request)
        finally:
            tmp.unlink(missing_ok=True)
        while time.monotonic()<deadline:
            current=advisor.snapshot()
            if current.session_id!=snapshot.session_id:raise ValueError('Session changed during read; rediscover game state')
            if not advisor.status(current)['live']:raise ValueError('Game observation is no longer fresh/loaded')
            try:result=load_json(response,2*1024*1024 if capture else 65536)
            except FileNotFoundError:result=None
            if isinstance(result,dict) and result.get('request_id')==request_id:
                if result.get('session_id')!=snapshot.session_id:raise ValueError('Read response belongs to a different session')
                if result.get('game_version')!=snapshot.game_version:raise ValueError('Read response version mismatch')
                captured=datetime.fromisoformat(result['captured_at'].replace('Z','+00:00'))
                if captured.tzinfo is None or not -2<=(datetime.now(timezone.utc)-captured).total_seconds()<=10:
                    raise ValueError('Read response timestamp is not recent')
                if result.get('available') is not True:raise ValueError(result.get('reason','Game read unavailable'))
                if capture and result.get("read_mode")!="capture":raise ValueError("Exporter did not return capture mode")
                data=result.get('data')
                if not isinstance(data,dict) or not isinstance(data.get('rows'),list) or len(data['rows'])>selection.limit:
                    raise ValueError('Invalid bounded entity response')
                if type(data.get('scanned_slots')) is not int or not 0<=data['scanned_slots']<=selection.scan_limit:
                    raise ValueError('Invalid scan bound')
                if capture and (data.get("next_cursor") is not None or data.get("predicate_errors")!=0):
                    raise ValueError("Incomplete capture; no selection retained")
                return result
            time.sleep(.05)
    raise ValueError('Game update did not answer the read request in time; inspect game_status and the game log')

ENTITY_QUERY_HELP = {
    'tool':'query_live_entities',
    'selection':EntitySelection.model_json_schema(),
    'boundary':'Fixed public entity getters and named individual statistics on the registered GAME.addAfterUpdate observer. Read-only; no arbitrary fields, methods or code.',
    'scope':'Current instantiated city or battlefield; unavailable without SETT. Not every game variable or private AI attribute.',
    'paging':'With entity_ids, the public getByID lookup is used and cursor indexes the requested ID list. Otherwise cursor indexes mutable scene-array slots. next_cursor continues from the scanned position, not the count of matching entities. Each page is a separate observation; no multi-page snapshot guarantee.',
    'limits':'10000 array slots scanned, 100 returned rows, four stat comparisons, 20 projected stats and 100 stat cells per request; 8 KiB request, 64 KiB response, 8-second deadline. POSIX MCP host required.',
    'relationships':'Optional relationships projection: recorded workplace room identity/blueprint/name/anchor; recorded profession blueprint; stored home-assignment coordinates; scene division identity/side. Per-getter available/data distinguish absent assignment from failed observation. Non-humanoids return null. These are not current activity, home occupancy, selected room, permanent IDs or a complete history. Requires the paired updated mod.',
    'units':'Raw stat integers and getter bounds do not establish semantic units. Cite returned reference_id and retrieve the installed description.',
}
