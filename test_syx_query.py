import json
from pathlib import Path
import pytest
from syx_mcp import Snapshot
from syx_query import QueryEngine, pointer

@pytest.fixture
def snapshot():
    s=json.loads(Path('snapshot.example.json').read_text())
    s['domains']['resources']['data']={'rows':[
        {'id':'grain','group':'food','amount':100,'capacity':200},
        {'id':'fish','group':'food','amount':10,'capacity':100},
        {'id':'wood','group':'material','amount':30,'capacity':None}]}
    s['domains']['production']={'coverage':'partial','reason':'fixture','data':{'rows':[
        {'id':'grain','delta':-5},{'id':'fish','delta':2}]}}
    return Snapshot.model_validate(s)

def run(s,q): return QueryEngine(s).execute({'queries':[q]})[0]
def source(): return {'domain':'resources','path':'/rows'}
def field(p): return {'field':p}

def test_filter_join_projection_sort(snapshot):
    q={'source':source(),'joins':[{'source':{'domain':'production','path':'/rows'},
        'left_key':'/id','right_key':'/id','as':'flow','kind':'left'}],
       'where':{'eq':[field('/group'),'food']},'select':{'resource':field('/id'),
       'fill':{'divide':[field('/amount'),field('/capacity')]},'delta':field('/flow/delta')},
       'sort':[{'field':'/fill','direction':'asc'}],'limit':1}
    result=run(snapshot,q)
    assert result['rows']==[{'resource':'fish','fill':.1,'delta':2}]
    assert result['matched_total']==2 and result['next_offset']==1
    assert result['source_coverage']=='partial'

def test_group_and_empty_aggregates(snapshot):
    q={'source':source(),'group_by':{'kind':field('/group')},'aggregates':{
        'total':{'op':'sum','value':field('/amount')},'n':{'op':'count'}}}
    assert run(snapshot,q)['rows']==[{'kind':'food','total':110,'n':2},{'kind':'material','total':30,'n':1}]
    q={'source':source(),'where':False,'aggregates':{'total':{'op':'sum','value':field('/amount')},'n':{'op':'count'}}}
    assert run(snapshot,q)['rows']==[{'total':None,'n':0}]

def test_null_and_missing_distinct(snapshot):
    q={'source':source(),'select':{'fill':{'divide':[field('/amount'),field('/capacity')]}}}
    assert run(snapshot,q)['rows'][-1]['fill'] is None
    with pytest.raises(ValueError,match='does not exist'):
        run(snapshot,{'source':source(),'select':{'x':field('/missing')}})
    with pytest.raises(ValueError): pointer({},'/bad~2escape')

@pytest.mark.parametrize('q',[
    {}, {'source':source(),'limit':101}, {'source':source(),'where':{'eval':'danger'}},
    {'source':source(),'joins':[{}]}, {'source':source(),'sort':[{}]},
    {'source':{'domain':'military'}}, {'source':source(),'select':{}},
    {'source':source(),'where':{'multiply':[True,2]}}])
def test_invalid_queries(snapshot,q):
    with pytest.raises(ValueError): run(snapshot,q)

def test_consistency_and_size(snapshot):
    with pytest.raises(ValueError,match='changed'):
        QueryEngine(snapshot).execute({'expected_snapshot_id':'wrong','queries':[{'source':source()}]})
    with pytest.raises(ValueError,match='64 KiB'):
        run(snapshot,{'source':source(),'select':{'x':{'literal':'x'*25000}}})


def test_join_retains_each_source_scope(snapshot):
    snapshot.domains['resources'].scope='instantiated_settlement_scene'
    snapshot.domains['production'].scope='campaign_player_or_faction'
    q={'source':source(),'joins':[{'source':{'domain':'production','path':'/rows'},
        'left_key':'/id','right_key':'/id','as':'flow','kind':'inner'}],
        'select':{'id':field('/id')}}
    result=run(snapshot,q)
    assert result['mixed_scopes'] is True
    assert [(s['domain'],s['scope']) for s in result['sources']]==[
        ('resources','instantiated_settlement_scene'),('production','campaign_player_or_faction')]


def test_context_expression_uses_same_snapshot(snapshot):
    from syx_mcp import Domain
    snapshot.domains['entities']=Domain(coverage='partial',reason='synthetic fixture',
        data={'items':[{'id':7},{'id':8}]})
    snapshot.ui_context={'selected_subject':{'entity_id':8},'known_overlay_active':True}
    q={'source':{'domain':'entities','path':'/items'},
       'where':{'eq':[{'field':'/id'},{'context':'/selected_subject/entity_id'}]}}
    result=QueryEngine(snapshot).execute({'queries':[q],'include_ui_context':True})[0]
    assert result['rows']==[{'id':8}]
    snapshot.ui_context['selected_subject']=None
    with pytest.raises(ValueError,match='does not exist'):run(snapshot,q)
    with pytest.raises(ValueError,match='boolean'):
        QueryEngine(snapshot).execute({'queries':[q],'include_ui_context':'yes'})


def test_unavailable_subtree_cannot_be_counted_or_joined_as_zero(snapshot):
    from syx_mcp import Domain
    snapshot.domains['trade']=Domain(coverage='partial',reason='mixed domain',data={
        'pipeline':{'coverage':'unavailable','scope':'city','reason':'Battlefield','rows':[]}})
    nested={'domain':'trade','path':'/pipeline/rows'}
    projected=run(snapshot,{'source':{'domain':'trade'},'select':{'stages':field('/pipeline/rows')}})
    assert projected['rows']==[{'stages':None}]
    with pytest.raises(ValueError,match='observation is unavailable'):
        run(snapshot,{'source':nested,'aggregates':{'n':{'op':'count'}}})
    with pytest.raises(ValueError,match='observation is unavailable'):
        run(snapshot,{'source':source(),'joins':[{'source':nested,'left_key':'/id','right_key':'/id','as':'trade','kind':'left'}]})
    snapshot.domains['trade'].data['pipeline']['nested']={'coverage':'partial','rows':[]}
    with pytest.raises(ValueError,match='observation is unavailable'):
        run(snapshot,{'source':{'domain':'trade','path':'/pipeline/nested/rows'}})
    snapshot.domains['trade'].data['pipeline']['coverage']='partial'
    assert run(snapshot,{'source':nested,'aggregates':{'n':{'op':'count'}}})['rows']==[{'n':0}]
    meta=run(snapshot,{'source':nested})['sources'][0]
    assert meta['subtree_scope']=='city' and meta['subtree_coverage']=='partial'


def test_collection_diagnostics_keep_ancestor_flags_and_join_provenance(snapshot):
    from syx_mcp import Domain
    snapshot.domains['services']=Domain(coverage='partial',reason='synthetic cap/failure case',data={
        'truncated':True,'row_limit':10000,'access/policy':{
            'coverage':'partial','scope':'city','truncated':False,'failed_service_types':2,
            'rule_row_limit':10000,'failure_samples':[{'reason':'not copied'}],
            'cohort_rules':[{'id':'grain','allowed':False}]}})
    src={'domain':'services','path':'/access~1policy/cohort_rules'}
    q={'source':src,'aggregates':{'observed':{'op':'count'}}}
    result=run(snapshot,q)
    expected=[{'path':'','truncated':True,'row_limit':10000},
        {'path':'/access~1policy','truncated':False,'failed_service_types':2,'rule_row_limit':10000}]
    assert result['rows']==[{'observed':1}]
    assert result['sources'][0]['collection_diagnostics']==expected
    joined=run(snapshot,{'source':source(),'joins':[{'source':src,'left_key':'/id','right_key':'/id','as':'policy'}]})
    assert joined['sources'][1]['collection_diagnostics']==expected
    assert joined['sources'][0]['collection_diagnostics']==[]


@pytest.mark.parametrize('rows,accepted',[(10000,True),(10001,False)])
def test_source_row_budget_boundary(snapshot,rows,accepted):
    snapshot.domains['resources'].data={'rows':[{'id':i} for i in range(rows)]}
    q={'source':source(),'aggregates':{'observed':{'op':'count'}}}
    if accepted:assert run(snapshot,q)['rows']==[{'observed':10000}]
    else:
        with pytest.raises(ValueError,match='Source exceeds row budget'):run(snapshot,q)


def test_duplicate_join_cannot_evade_row_cap_with_small_page(snapshot):
    snapshot.domains['resources'].data={'rows':[{'id':0} for _ in range(101)]}
    snapshot.domains['production'].data={'rows':[{'id':0} for _ in range(100)]}
    with pytest.raises(ValueError,match='Join result exceeds row budget'):
        run(snapshot,{'source':source(),'joins':[{'source':{'domain':'production','path':'/rows'},
            'left_key':'/id','right_key':'/id','as':'flow'}],'limit':1})


def test_batch_work_budget_is_shared(snapshot):
    snapshot.domains['resources'].data={'rows':[{'id':i} for i in range(10000)]}
    q={'source':source(),'select':{'id':field('/id')},'limit':1}
    assert len(QueryEngine(snapshot).execute({'queries':[q]*10}))==10
    q['select']['copy']=field('/id')
    with pytest.raises(ValueError,match='work budget'):
        QueryEngine(snapshot).execute({'queries':[q]*10})


def test_degradation_example_sorts_projected_values_and_keeps_null_staffing(snapshot):
    from syx_mcp import Domain
    rows=[{'room_id':room,'direction':'output','resource_id':'wood','room_degradation_raw':value,'previous_day_units':10}
          for room,value in [(1,.2),(2,.8),(3,0),(4,None)]]
    rows.append({'room_id':5,'direction':'input','resource_id':'wood','room_degradation_raw':1,'previous_day_units':10})
    snapshot.domains['production']=Domain(coverage='partial',reason='Synthetic example regression; not room integration.',
        data={'room_data':{'flows':rows}})
    worker={'room_id':1,'employed':9}
    snapshot.domains['employment']=Domain(coverage='partial',reason='Synthetic staffing fixture.',data={'rooms':[worker]})
    spec=json.loads(Path('degradation-query-example.json').read_text())
    result=QueryEngine(snapshot).execute(spec)[0]
    assert result['matched_total']==4
    assert result['rows']==[
        {'room':room,'resource':'wood','degradation':value,'recorded_previous_day':10,'staffing':worker if room==1 else None}
        for room,value in [(2,.8),(1,.2),(3,0),(4,None)]]


def test_housing_scan_and_read_failures_survive_aggregate_and_join(snapshot):
    from syx_mcp import Domain
    diagnostics={'room_slots_scanned':12,'room_map_size':90,'scan_limit':12,
                 'room_scan_complete':False,'failed_room_reads':1,'failed_rosters':2,
                 'truncated_rosters':3,'row_limit':10}
    snapshot.domains['housing']=Domain(coverage='partial',scope='instantiated_settlement_scene',data={
        'home_records':{'coverage':'partial','scope':'instantiated_city_home_records',
                        'data':{**diagnostics,'rooms':[{'id':'grain','occupants':4}]}}})
    source={'domain':'housing','path':'/home_records/data/rooms'}
    aggregate=run(snapshot,{'source':source,'aggregates':{'n':{'op':'count'}}})
    expected=[{'path':'/home_records/data',**diagnostics}]
    assert aggregate['rows']==[{'n':1}]
    assert aggregate['sources'][0]['collection_diagnostics']==expected
    assert aggregate['sources'][0]['subtree_scope']=='instantiated_city_home_records'
    joined=run(snapshot,{'source':{'domain':'resources','path':'/rows'},
        'joins':[{'source':source,'left_key':'/id','right_key':'/id','as':'home'}],
        'select':{'id':field('/id')}})
    assert joined['sources'][0]['collection_diagnostics']==[]
    assert joined['sources'][1]['collection_diagnostics']==expected


def test_housing_diagnostics_never_copy_strings_rows_or_descendants():
    from syx_query import collection_diagnostics
    node={'home_records':{'data':{'failed_room_reads':'private exception text',
          'failed_rosters':['private resident IDs'],'truncated_rosters':{'private':'body'},
          'room_scan_complete':False,'scan_limit':12,
          'rows':[{'failed_room_reads':999,'private':'row values'}]}}}
    assert collection_diagnostics(node,'/home_records/data/rows')==[
        {'path':'/home_records/data','room_scan_complete':False,'scan_limit':12}]
    assert collection_diagnostics(node,'/home_records')==[]


def test_housing_zero_errors_and_complete_scan_are_not_dropped():
    from syx_query import collection_diagnostics
    data={'room_slots_scanned':90,'room_map_size':90,'scan_limit':10000,
          'room_scan_complete':True,'failed_room_reads':0,'failed_rosters':0,'truncated_rosters':0}
    assert collection_diagnostics({'data':{**data,'rooms':[]}},'/data/rooms')==[{'path':'/data',**data}]
