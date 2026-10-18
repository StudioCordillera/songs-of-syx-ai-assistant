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
