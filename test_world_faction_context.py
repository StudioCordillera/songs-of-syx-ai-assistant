"""The player example selects the context faction and refuses a missing identity."""
import json
from pathlib import Path
import pytest
from syx_mcp import Snapshot
from syx_query import QueryEngine


def observation(identity):
    raw=json.loads(Path('snapshot.example.json').read_text())
    raw['ui_context']={'active_view':'world','world_faction_panels':{
        'coverage':'partial','list_open':True,'detail_faction':None if identity is None else
        {'faction_id':identity,'diplomacy_tab':True},'identity_search_complete':True}}
    raw['domains']['diplomacy']={'coverage':'partial','data':{'factions':[
        {'id':11,'name':'Fixture first','stance':'neutral'},
        {'id':23,'name':'Fixture other','stance':'war'}]}}
    return Snapshot.model_validate(raw)


@pytest.mark.parametrize('identity,name,stance',[(11,'Fixture first','neutral'),(23,'Fixture other','war')])
def test_authored_context_query_selects_identity_instead_of_first_row(identity,name,stance):
    example=json.loads(Path('world-faction-query-example.json').read_text())
    rows=QueryEngine(observation(identity)).execute({'queries':example['queries']})
    assert rows[0]['rows']==[{'faction_id':identity,'name':name,'stance':stance}]
    assert rows[0]['matched_total']==1


def test_missing_detail_identity_is_refused_instead_of_defaulting_to_a_faction():
    example=json.loads(Path('world-faction-query-example.json').read_text())
    with pytest.raises(ValueError,match='Field does not exist'):
        QueryEngine(observation(None)).execute({'queries':example['queries']})
