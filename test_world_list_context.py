"""Context booleans are observation-scoped; unavailable list presence never becomes false."""
import json
from pathlib import Path
import pytest
from syx_mcp import Snapshot
from syx_query import QueryEngine


@pytest.mark.parametrize('value',[True,False,None])
def test_membership_projection_keeps_true_false_and_unavailable_distinct(value):
    data=json.loads(Path('snapshot.example.json').read_text())
    data['ui_context']={'world_list_panels':{'coverage':'unavailable' if value is None else 'partial',
        'army_list_present':value,'player_realm_list_present':value,'region_browser_present':value}}
    data['domains']['world']={'coverage':'partial','data':{'regions':[{'id':7}]}}
    snapshot=Snapshot.model_validate(data)
    spec={'expected_snapshot_id':snapshot.snapshot_id,'include_ui_context':True,'queries':[{
        'source':{'domain':'world','path':'/regions'},'select':{'id':{'field':'/id'},
        'present':{'context':'/world_list_panels/army_list_present'}}}]}
    result=QueryEngine(snapshot).execute(spec)[0]
    assert result['rows']==[{'id':7,'present':value}] and type(result['rows'][0]['present']) is type(value)
    with pytest.raises(ValueError,match='Snapshot changed'):
        QueryEngine(snapshot).execute({**spec,'expected_snapshot_id':'other-observation'})
    snapshot.ui_context={'selected_world_region':None}
    with pytest.raises(ValueError,match='does not exist'):QueryEngine(snapshot).execute(spec)
