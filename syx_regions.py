"""Fixed live campaign resource-output reads, independent of cached row-prefix contents."""
import base64
from typing import Annotated,Literal
from pydantic import Field,StrictInt,StrictStr,model_validator
from syx_live import StrictModel,_read_entities

Nonnegative=Annotated[StrictInt,Field(ge=0,le=2**31-1)]
RegionId=Annotated[StrictInt,Field(ge=0,le=1022)]
ResourceKey=Annotated[StrictStr,Field(min_length=1,max_length=100)]


class RegionalSelection(StrictModel):
    region_ids:list[RegionId]=Field(min_length=1,max_length=100)
    resource_ids:list[ResourceKey]=Field(min_length=1,max_length=100)
    fields:list[Literal['accrued_output_raw','days_until_configured_output','reference_id','faction_id']]=Field(
        default_factory=lambda:['accrued_output_raw','days_until_configured_output'],min_length=1,max_length=4)
    min_accrued_output:Nonnegative|None=None
    max_accrued_output:Nonnegative|None=None
    faction_id:Nonnegative|None=None
    cursor:Annotated[StrictInt,Field(ge=0,le=10000)]=0
    scan_limit:Annotated[StrictInt,Field(ge=1,le=4096)]=4096
    limit:Annotated[StrictInt,Field(ge=1,le=100)]=25
    expected_session_id:StrictStr|None=None

    @model_validator(mode='after')
    def matrix_and_range(self):
        for values in [self.region_ids,self.resource_ids,self.fields]:
            if len(values)!=len(set(values)):raise ValueError('Duplicate regional selection item')
        if self.cursor>len(self.region_ids)*len(self.resource_ids):raise ValueError('Cursor exceeds requested matrix')
        if self.min_accrued_output is not None and self.max_accrued_output is not None and self.min_accrued_output>self.max_accrued_output:
            raise ValueError('Accrued minimum exceeds maximum')
        return self

    def wire(self,request_id,session,expires):
        def optional(value):return '' if value is None else str(value)
        keys=[base64.urlsafe_b64encode(k.encode()).decode().rstrip('=') for k in self.resource_ids]
        values={'protocol':'1','request_id':request_id,'session':session,'expires':expires,
            'regions':','.join(map(str,self.region_ids)),'resources':','.join(keys),'fields':','.join(self.fields),
            'cursor':self.cursor,'scan_limit':self.scan_limit,'limit':self.limit,
            'minimum':optional(self.min_accrued_output),'maximum':optional(self.max_accrued_output),'faction':optional(self.faction_id)}
        text=''.join(f'{k}={v}\n' for k,v in values.items())
        if len(text.encode())>8192:raise ValueError('Regional request exceeds 8 KiB')
        return text


def query_regional_outputs(advisor,spec,*,timeout=8):
    selection=RegionalSelection.model_validate(spec)
    result=_read_entities(advisor,selection,timeout=timeout,channel='regional')
    data=result['data'];area=len(selection.region_ids)*len(selection.resource_ids)
    if (result.get('read_mode')!='regional_page' or result.get('observer_phase')!='GAME.addAfterUpdate' or
        result.get('scope')!='campaign_world_regions' or result.get('coverage')!='partial' or
        data.get('cursor_kind')!='requested_region_resource_matrix' or
        data.get('region_ids')!=selection.region_ids or data.get('resource_ids')!=selection.resource_ids):
        raise ValueError('Invalid regional response identity/scope')
    scanned=data['scanned_cells'];end=selection.cursor+scanned;cursor=data.get('next_cursor')
    if ((scanned==0 and selection.cursor<area) or end>area or
        (cursor is not None and (type(cursor) is not int or cursor!=end or end>=area)) or (cursor is None and end!=area)):
        raise ValueError('Invalid regional response cursor')
    errors=data.get('cell_errors')
    if type(errors) is not int or not 0<=errors<=scanned or len(data['rows'])+errors>scanned:
        raise ValueError('Invalid regional cell/error counts')
    if data.get('region_scan_limit')!=1023 or data.get('resource_scan_limit')!=1000:raise ValueError('Invalid registry scan limits')
    for key,bound in [('scanned_regions',1023),('scanned_resources',1000)]:
        if type(data.get(key)) is not int or not 0<=data[key]<=bound:raise ValueError('Invalid registry scan bound')
    if not isinstance(result.get('scene'),dict) or not isinstance(result.get('ui_context'),dict) or type(result.get('tick')) is not int or result['tick']<0:
        raise ValueError('Missing regional response context')
    last=selection.cursor-1
    for row in data['rows']:
        if not isinstance(row,dict) or set(row)!={'region_id','resource_id',*selection.fields}:
            raise ValueError('Invalid regional row projection')
        rid,res=row['region_id'],row['resource_id']
        if type(rid) is not int or rid not in selection.region_ids or type(res) is not str or res not in selection.resource_ids:
            raise ValueError('Regional row exceeds requested identities')
        position=selection.region_ids.index(rid)*len(selection.resource_ids)+selection.resource_ids.index(res)
        if not max(selection.cursor,last+1)<=position<end:raise ValueError('Duplicate/out-of-order regional matrix position')
        last=position
        for field in ['accrued_output_raw','days_until_configured_output','faction_id']:
            if field not in selection.fields:continue
            value=row[field]
            if field=='faction_id' and value is None:continue
            if type(value) is not int or not 0<=value<=2**31-1:raise ValueError('Invalid regional numeric field')
        value=row.get('accrued_output_raw')
        if value is not None and ((selection.min_accrued_output is not None and value<selection.min_accrued_output) or
                (selection.max_accrued_output is not None and value>selection.max_accrued_output)):
            raise ValueError('Regional row violates accrued predicate')
        if 'faction_id' in row and selection.faction_id is not None and row['faction_id']!=selection.faction_id:
            raise ValueError('Regional row violates faction predicate')
        if 'reference_id' in selection.fields and row['reference_id']!='resource:'+res:raise ValueError('Invalid regional resource reference')
    from pydantic_core import to_json
    if len(to_json(result,indent=2,fallback=str))>65536:raise ValueError('Regional tool text exceeds 64 KiB; narrow fields/limit')
    return result


REGIONAL_QUERY_HELP={
    'tool':'query_live_regional_outputs','selection':RegionalSelection.model_json_schema(),
    'boundary':'Fixed public campaign resource-output getters in GAME.addAfterUpdate, detached DTOs only. No cached row source, private reflection, boost/cache refresh, shipping action or arbitrary member invocation.',
    'identities':'Explicit active region IDs and exact loaded resource keys; unknown/inactive identities fail the request, never become zero counters. Same session required; no UI-selected region inference.',
    'paging':'Cursor is a position in the requested region_ids x resource_ids ordered matrix, not a global game slot or matching-row count. Supply the same ordered IDs/predicates/fields for continuation. Follow next_cursor even after empty filtered pages. Every page has its own request/tick/time/scene/UI; no multi-page consistency or retained capture is established.',
    'limits':'100 region IDs/100 resource keys, at most 1023 region and 1000 resource registry bindings, 4096 cells scanned/100 returned rows per page, 8 KiB request/64 KiB response, eight-second deadline. Cell errors qualify absence/count. POSIX transport serializes this with entity/tile requests.',
    'semantics':'accrued_output_raw is stored resource-backed campaign accrual, not inventory, annual delivered totals, income/production forecast. days_until_configured_output is a cyclic schedule offset, not departure/arrival ETA or shipping permission. Exact age is unknown. faction_id is current campaign ownership in this response, not cached UI selection. Non-resource/MONEY outputs remain excluded. Public source verified, not documented stable contracts.',
    'provenance':['REGIONAL_OUTPUT_BOUNDARY_REVIEW.json','REGIONAL_OUTPUTS.md','REGIONAL_LIVE_READS.md']}
