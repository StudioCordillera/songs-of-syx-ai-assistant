"""Production detached adapter and snapshot-cache integration; synthetic JSON is not native evidence."""
import json
from pathlib import Path
from copy import deepcopy
from syx_housing import attach_view,build_view
from syx_mcp import Advisor
from test_housing_query_view import candidate


def test_production_adapter_matches_reviewed_candidate():
    from dev.housing_query_view import build_view as reviewed
    c=candidate()
    assert build_view(c)==reviewed(c)


def test_attach_preserves_existing_data_and_descriptions():
    d={'statistics':[{'id':'stored'}],'field_definitions':{'existing':'unchanged'},'home_records':candidate()}
    attach_view(d,'0.71.44')
    assert d['statistics']==[{'id':'stored'}] and d['field_definitions']['existing']=='unchanged'
    assert len(d['home_assignments']['data']['rows'])==3


def test_legacy_and_unavailable_sources_do_not_invent_tables():
    d={'statistics':[]};before=deepcopy(d);attach_view(d,'0.71.44');assert d==before
    d={'home_records':{'available':False,'coverage':'unavailable','scope':'instantiated_city_home_records','data':None,'reason':'No city'}}
    attach_view(d,'0.71.44');assert d['home_assignments']['data'] is None


def test_bad_contract_and_unsupported_version_refuse_without_losing_aggregates():
    for version,c in [('0.71.45',candidate()),('0.71.44',{'available':True})]:
        d={'statistics':[1],'home_records':c};attach_view(d,version)
        assert d['statistics']==[1]
        for key in ['home_records','home_assignments']:
            assert d[key]['coverage']=='unavailable' and d[key]['data'] is None


def test_derived_cache_updates_once_per_observation_and_keeps_identity(tmp_path):
    raw=json.loads(Path('snapshot.example.json').read_text());raw['game_version']='0.71.44'
    raw['domains']['housing']={'coverage':'partial','reason':'test','data':{'home_records':candidate()}}
    path=tmp_path/'snapshot.json';path.write_text(json.dumps(raw))
    a=Advisor(path,tmp_path/'absent.json');one=a.snapshot()
    assert a.snapshot() is one and one.snapshot_id==raw['snapshot_id'] and one.ui_context==raw.get('ui_context',{})
    assert len(one.domains['housing'].data['home_assignments']['data']['rows'])==3
    raw['snapshot_id']='next';raw['domains']['housing']['data']['home_records']=candidate((0,))
    path.write_text(json.dumps(raw));two=a.snapshot()
    assert two is not one and two.snapshot_id=='next' and two.domains['housing'].data['home_assignments']['data']['rows']==[]
    assert len(one.domains['housing'].data['home_assignments']['data']['rows'])==3
