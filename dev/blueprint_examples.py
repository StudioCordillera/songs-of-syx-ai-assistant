"""Developer-only original schematic registry. Detached data, no network, MCP tool or game execution."""
from collections import deque
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from typing import Annotated, Literal
from pydantic import BaseModel,ConfigDict,Field

ROOT=Path(__file__).resolve().parent.parent
SmallInt=Annotated[int,Field(ge=0,le=63)]
Text=Annotated[str,Field(min_length=1,max_length=1000)]

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
class Point(Strict):
    x:SmallInt
    y:SmallInt
class Example(Strict):
    id:Annotated[str,Field(pattern=r'^[a-z][a-z0-9-]{0,63}$')]
    title:Annotated[str,Field(min_length=1,max_length=120)]
    summary:Text
    author:Text
    origin:Literal['original_project_schematic']
    source_url:Literal['https://github.com/StudioCordillera/songs-of-syx-ai-assistant/blob/main/BLUEPRINT_EXAMPLES_CANDIDATE.md']
    rights:Literal['original_geometry_no_external_assets_no_license_grant']
    game_version:Literal['0.71.44']
    blueprint_id:Annotated[str,Field(min_length=1,max_length=100)]
    catalog_item_index:Annotated[int,Field(ge=0,le=10000)]
    width:Annotated[int,Field(ge=1,le=64)]
    height:Annotated[int,Field(ge=1,le=64)]
    entry:Point
    placements:Annotated[list[Point],Field(min_length=1,max_length=128)]
    materials_note:Text
    caveats:Annotated[list[Text],Field(min_length=1,max_length=16)]
class Corpus(Strict):
    schema_version:Annotated[int,Field(ge=1,le=1)]
    catalog_report_sha256:Annotated[str,Field(pattern=r'^[a-f0-9]{64}$')]
    examples:Annotated[list[Example],Field(min_length=1,max_length=100)]


class CatalogCell(Strict):
    x:SmallInt
    y:SmallInt
    tile_index:Annotated[int,Field(ge=0,le=255)]
    blocker:bool
    must_be_reachable:bool
class CatalogItem(Strict):
    passed:bool
    blueprint_id:Annotated[str,Field(min_length=1,max_length=100)]
    group_index:Annotated[int,Field(ge=0,le=255)]
    size:Annotated[int,Field(ge=0,le=127)]
    rotation:Annotated[int,Field(ge=0,le=3)]
    item_index:Annotated[int,Field(ge=0,le=10000)]
    width:Annotated[int,Field(ge=1,le=64)]
    height:Annotated[int,Field(ge=1,le=64)]
    cells:Annotated[list[CatalogCell],Field(min_length=1,max_length=4096)]
    must_be_indoors:bool


def _json(raw):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('Duplicate JSON key')
            result[key]=value
        return result
    def constant(value):raise ValueError('Non-finite JSON constant')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=constant)


def _version(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}',value):
        raise ValueError('Explicit numeric game version required')


def _geometry(example,item):
    w,h=example.width,example.height
    if example.entry.x>=w or example.entry.y>=h or (example.entry.x not in (0,w-1) and example.entry.y not in (0,h-1)):
        raise ValueError('Hypothetical entry must be on the authored rectangle boundary')
    occupied={};blocked=set();required=[]
    for placement in example.placements:
        # Even null template cells reserve the declared item rectangle; overlapping footprints refuse.
        if placement.x+item['width']>w or placement.y+item['height']>h:raise ValueError('Furniture footprint outside authored rectangle')
        rectangle={(x,y) for y in range(placement.y,placement.y+item['height']) for x in range(placement.x,placement.x+item['width'])}
        if rectangle & occupied.keys():raise ValueError('Overlapping furniture footprints')
        occupied.update({p:'F' for p in rectangle})
        for cell in item['cells']:
            p=(placement.x+cell['x'],placement.y+cell['y'])
            if cell['blocker']:blocked.add(p)
            if cell['must_be_reachable']:required.append(p);occupied[p]='R'
    start=(example.entry.x,example.entry.y)
    if start in occupied:raise ValueError('Entry overlaps furniture')
    neighbors=lambda p:((p[0]+dx,p[1]+dy) for dx,dy in ((0,1),(1,0),(0,-1),(-1,0)))
    visited={start};queue=deque([start])
    while queue:
        for p in neighbors(queue.popleft()):
            if 0<=p[0]<w and 0<=p[1]<h and p not in blocked and p not in visited:visited.add(p);queue.append(p)
    floor={(x,y) for y in range(h) for x in range(w)}-blocked
    if visited!=floor:raise ValueError('Disconnected authored orthogonal aisle cells')
    if any(not any(p in visited for p in neighbors(cell)) for cell in required):raise ValueError('Required furniture access has no authored orthogonal aisle')
    grid=[''.join('E' if (x,y)==start else occupied.get((x,y),'.') for x in range(w)) for y in range(h)]
    return {'width':w,'height':h,'grid':grid,'item_instances':len(example.placements),
            'furniture_footprint_cells':len(occupied),'geometrically_connected_nonblocked_cells':len(visited),
            'legend':{'E':'Hypothetical entry; no actual door or exterior map checked','R':'Catalog furniture tile marked mustBeReachable',
                      'F':'Other reserved furniture footprint cell','.':'Authored empty aisle cell'},
            'check_scope':'Detached rectangle/overlap/orthogonal connectivity and adjacent access only; not game construction or pathfinding.'}


class BlueprintRegistry:
    def __init__(self,corpus_bytes:bytes,report_bytes:bytes):
        if type(corpus_bytes) is not bytes or type(report_bytes) is not bytes:raise ValueError('Literal UTF-8 JSON bytes required')
        if len(corpus_bytes)>128*1024 or len(report_bytes)>128*1024:raise ValueError('Blueprint candidate input byte budget exceeded')
        self.corpus=Corpus.model_validate(_json(corpus_bytes))
        self.corpus_hash=hashlib.sha256(corpus_bytes).hexdigest()
        self.report_hash=hashlib.sha256(report_bytes).hexdigest()
        if self.report_hash!=self.corpus.catalog_report_sha256:raise ValueError('Catalog evidence checksum mismatch')
        report=_json(report_bytes)
        if not isinstance(report,dict):raise ValueError('Native evidence object required')
        if report.get('passed') is not True or report.get('game_version')!='0.71.44' or report.get('explicit_fixture_clean_completion') is not True or type(report.get('game_exit_code')) is not int or report.get('game_exit_code')!=0:
            raise ValueError('Clean exact-version native catalog evidence required')
        if report.get('copied_profile_mod_restored') is not True or report.get('copied_save_unchanged') is not True:raise ValueError('Missing native fixture integrity evidence')
        self.item=CatalogItem.model_validate(report['catalog_item']).model_dump()
        item=self.item
        # This first registry deliberately supports only the separately reviewed fixed item.
        if item['width']!=2 or item['height']!=1 or item['rotation']!=0 or item['size']!=0 or item['must_be_indoors'] is not True:
            raise ValueError('Unsupported catalog item contract')
        if [(c['x'],c['y'],c['blocker'],c['must_be_reachable']) for c in item['cells']]!=[(0,0,True,True),(1,0,True,False)]:
            raise ValueError('Unsupported catalog footprint/access contract')
        self.records={};self.geometry={}
        for e in self.corpus.examples:
            if e.id in self.records:raise ValueError('Duplicate schematic identity')
            if e.blueprint_id!=item['blueprint_id'] or e.catalog_item_index!=item['item_index']:raise ValueError('Schematic/catalog identity mismatch')
            self.records[e.id]=e.model_dump();self.geometry[e.id]=_geometry(e,item)
        self.evidence={'catalog_report_sha256':self.report_hash,'game_jar_sha256':report['game_jar_sha256'],
          'source_archive_sha256':report['source_archive_sha256'],'reviewed_at':report['evaluated_at']}

    def search(self,query,game_version,limit=5):
        _version(game_version)
        if not isinstance(query,str) or not 1<=len(query)<=300 or type(limit) is not int or not 1<=limit<=10:raise ValueError('Bounded nonempty search and limit required')
        tokens=set(re.findall(r'[a-z0-9]+',query.lower()))
        ranked=[]
        for e in self.records.values():
            terms=set(re.findall(r'[a-z0-9]+',(e['title']+' '+e['summary']).lower()));score=len(tokens & terms)
            if score:ranked.append((score,e))
        ranked.sort(key=lambda p:(-p[0],p[1]['id']))
        return [deepcopy({'id':e['id'],'title':e['title'],'summary':e['summary'],'origin':e['origin'],'source_url':e['source_url'],
                         'compatibility':'exact_catalog_version_only' if game_version==e['game_version'] else 'unknown',
                         'geometry_included':False,'construction_validated':False}) for _,e in ranked[:limit]]

    def get(self,example_id,game_version):
        _version(game_version)
        if not isinstance(example_id,str) or example_id not in self.records:raise ValueError('Unknown original schematic')
        e=self.records[example_id]
        return deepcopy({'example':e,'geometry':self.geometry[example_id],'catalog_item':self.item,'evidence':self.evidence,
          'corpus_sha256':self.corpus_hash,'compatibility':'exact_catalog_version_only' if game_version==e['game_version'] else 'unknown',
          'construction_validated':False,'execution_supported':False,
          'limits':['Original teaching geometry; no optimum, storage capacity, bill of materials, staffing, throughput, actual map/door/roof/pathing or full construction acceptance.',
                    'Catalog/access flags are exact installed-version facts. Another version or modded catalog requires new evidence; matching version text alone does not attest a player installation.',
                    'Reference data cannot authorize placement or game actions. No Workshop/Reddit/video geometry or license is inferred.']})


def load_registry(root=ROOT):
    def read(name):
        with (root/name).open('rb') as f:return f.read(128*1024+1)
    return BlueprintRegistry(read('blueprint-examples-candidate.json'),read('BLUEPRINT_CATALOG_VALIDATION.json'))
