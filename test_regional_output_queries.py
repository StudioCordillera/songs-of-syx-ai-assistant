"""Authored campaign accrual query, observed zero and qualified incomplete/missing data."""
import json
from pathlib import Path
import pytest
from syx_mcp import Snapshot
from syx_query import QueryEngine


def data():
    raw=json.loads(Path('snapshot.example.json').read_text())
    raw['domains']['world']={'coverage':'partial','scope':'campaign_world_regions','data':{
        'regions':[{'id':1,'name':'Fixture one','faction_id':7},{'id':2,'name':'Fixture other','faction_id':None}],
        'regional_output_bookkeeping':{'coverage':'partial','scope':'campaign_world_regions',
            'rows':[{'region_id':2,'resource_id':'wood','reference_id':'resource:wood','accrued_output_raw':0},
                {'region_id':1,'resource_id':'grain','reference_id':'resource:grain','accrued_output_raw':13},
                {'region_id':2,'resource_id':'grain','reference_id':'resource:grain','accrued_output_raw':5}],
            'schedules':[{'resource_id':'grain','days_until_configured_output':3},
                {'resource_id':'wood','days_until_configured_output':0}],
            'scanned_resources':2,'resource_count_total':2,'resource_limit':1000,'failed_resources':0,'resource_truncated':False,
            'scanned_regions':2,'region_limit':1023,'region_truncated':False,
            'scanned_cells':3,'cell_limit':10000,'row_limit':10000,'failed_cells':0,'cell_truncated':False,'truncated':False}}}
    return raw


def example():return {'queries':json.loads(Path('regional-output-query-example.json').read_text())['queries']}


def test_authored_query_joins_region_and_cyclic_schedule_without_city_inventory():
    rows=QueryEngine(Snapshot.model_validate(data())).execute(example())[0]
    assert rows['rows']==[
        {'region_id':1,'region':'Fixture one','faction_id':7,'resource':'grain','accrued_output':13,'configured_days':3,'reference_id':'resource:grain'},
        {'region_id':2,'region':'Fixture other','faction_id':None,'resource':'grain','accrued_output':5,'configured_days':3,'reference_id':'resource:grain'}]
    assert rows['matched_total']==2


def test_failed_and_capped_cell_diagnostics_qualify_exported_aggregate_count():
    raw=data();book=raw['domains']['world']['data']['regional_output_bookkeeping']
    book.update(scanned_cells=4,failed_cells=1,cell_truncated=True,truncated=True,resource_truncated=True,failed_resources=1)
    query={'queries':[{'source':{'domain':'world','path':'/regional_output_bookkeeping/rows'},'aggregates':{'n':{'op':'count'}}}]}
    result=QueryEngine(Snapshot.model_validate(raw)).execute(query)[0]
    assert result['rows']==[{'n':3}]
    diag=result['sources'][0]['collection_diagnostics']
    assert any(d['path']=='/regional_output_bookkeeping' and d['scanned_cells']==4 and d['failed_cells']==1 and
        d['cell_limit']==10000 and d['resource_truncated'] and d['failed_resources']==1 for d in diag)


@pytest.mark.parametrize('path',['/regional_output_bookkeeping/rows','/regional_output_bookkeeping/schedules'])
def test_unavailable_regional_observation_is_refused_instead_of_an_empty_count(path):
    raw=data();raw['domains']['world']['data']['regional_output_bookkeeping']={'coverage':'unavailable','rows':None,'schedules':None}
    with pytest.raises(ValueError,match='observation is unavailable'):
        QueryEngine(Snapshot.model_validate(raw)).execute({'queries':[{'source':{'domain':'world','path':path},'aggregates':{'n':{'op':'count'}}}]})


def test_observed_zero_and_zero_cyclic_offset_remain_numeric_values():
    raw=data();spec=example();spec['queries'][0]['where']={'eq':[{'field':'/resource_id'},'wood']}
    row=QueryEngine(Snapshot.model_validate(raw)).execute(spec)[0]['rows'][0]
    assert row['accrued_output']==0 and row['configured_days']==0
