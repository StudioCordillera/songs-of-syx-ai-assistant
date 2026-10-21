"""Selected-person/home/staffing query composition and qualified absence; synthetic, not native evidence."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from syx_mcp import Snapshot
from syx_query import QueryEngine

ROOT=Path(__file__).resolve().parent

def fixture():
    raw=json.loads((ROOT/'snapshot.example.json').read_text())
    raw['domains']['entities']={'coverage':'partial','scope':'instantiated_settlement_scene','data':{'items':[], 'selected_subject':{
        'entity_id':41,'relationships':{'workplace':{'available':True,'data':{'room_id':12}},'home_assignment':{'available':True,'data':{'tile_x':7,'tile_y':8}}}}}}
    raw['domains']['housing']={'coverage':'partial','scope':'instantiated_city','data':{
        'home_assignments':{'available':True,'coverage':'partial','scope':'instantiated_city_recorded_home_assignments','data':{'rows':[{'resident_id':41,'room_id':9,'roster_index':0}],'room_scan_complete':True,'failed_rosters':0}},
        'home_records':{'available':True,'coverage':'partial','scope':'instantiated_city_home_records','data':{'rooms':[{'room_id':9,'kind':'ordinary_home','service_tile_x':7,'service_tile_y':8,'capacity_configured':3}],'room_scan_complete':True,'failed_room_reads':0}}}}
    raw['domains']['employment']={'coverage':'partial','scope':'instantiated_city','data':{'rooms':[{'room_id':12,'employed':2}],'truncated':False}}
    return raw

def execute(raw):
    spec=json.loads((ROOT/'selected-resident-query-example.json').read_text())
    return QueryEngine(Snapshot.model_validate(raw)).execute(spec)[0]

def test_three_join_example_keeps_keys_and_all_source_metadata():
    r=execute(fixture());row=r['rows'][0]
    assert row=={'entity_id':41,'recorded_home_room_id':9,'home_kind':'ordinary_home','home_service_tile_x':7,'home_service_tile_y':8,'configured_home_capacity':3,'person_recorded_home_tile':{'tile_x':7,'tile_y':8},'recorded_workplace_room_id':12,'observed_workplace':{'room_id':12,'employed':2}}
    assert len(r['sources'])==4 and r['matched_total']==1
    assert [s['domain'] for s in r['sources']]==['entities','housing','housing','employment']

def test_missing_cached_workplace_stays_null_with_prefix_diagnostic():
    raw=fixture();raw['domains']['employment']['data']={'rooms':[],'truncated':True}
    r=execute(raw);assert r['rows'][0]['recorded_workplace_room_id']==12 and r['rows'][0]['observed_workplace'] is None
    assert any(x.get('truncated') is True for x in r['sources'][-1]['collection_diagnostics'])

def test_missing_home_prefix_is_qualified_zero_matches_not_unhoused_census():
    raw=fixture();d=raw['domains']['housing']['data']['home_assignments']['data'];d['rows']=[];d['room_scan_complete']=False
    r=execute(raw);assert r['rows']==[] and r['matched_total']==0
    assert any(x.get('room_scan_complete') is False for x in r['sources'][1]['collection_diagnostics'])

def test_duplicate_recorded_links_are_preserved_not_silently_deduplicated():
    raw=fixture();rows=raw['domains']['housing']['data']['home_assignments']['data']['rows'];rows.append(deepcopy(rows[0]))
    assert execute(raw)['matched_total']==2

@pytest.mark.parametrize('change',['no_selection','no_recorded_workplace','housing_unavailable'])
def test_unsupported_example_preconditions_refuse_instead_of_guessing(change):
    raw=fixture()
    if change=='no_selection':raw['domains']['entities']['data']['selected_subject']=None
    elif change=='no_recorded_workplace':raw['domains']['entities']['data']['selected_subject']['relationships']['workplace']['data']=None
    else:raw['domains']['housing']['data']['home_records']={'available':False,'coverage':'unavailable','data':None}
    with pytest.raises(ValueError):execute(raw)
