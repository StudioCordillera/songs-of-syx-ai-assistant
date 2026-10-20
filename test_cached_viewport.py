"""Cached geometry is observation data; unavailable never becomes a zero rectangle."""
import pytest
from syx_query import QueryEngine
from syx_api_support import CAPABILITIES
from test_syx_query import snapshot


@pytest.mark.parametrize('available',[True,False])
def test_camera_context_keeps_negative_bounds_and_unavailable_distinct(snapshot,available):
    data={'tiles':[-2,5,30,40],'pixels':[-64,160,960,1280],'screen':[0,0,1024,1120],
          'map_bounds_tiles':[0,0,512,512],'zoomout':0} if available else None
    snapshot.ui_context={'cached_viewport':{'available':available,'coverage':'partial' if available else 'unavailable',
        'data':data,'cache_age_known':False,'rendered_visibility_known':False}}
    spec={'expected_snapshot_id':snapshot.snapshot_id,'include_ui_context':True,'queries':[{
        'source':{'domain':'resources','path':'/rows'},'limit':1,
        'select':{'resource':{'field':'/id'},'camera':{'context':'/cached_viewport/data'},
                  'available':{'context':'/cached_viewport/available'}}}]}
    result=QueryEngine(snapshot).execute(spec)[0]
    assert result['rows']==[{'resource':'grain','camera':data,'available':available}]
    with pytest.raises(ValueError,match='Snapshot changed'):
        QueryEngine(snapshot).execute({**spec,'expected_snapshot_id':'different'})


def test_cached_geometry_capability_distinguishes_contract_and_selection():
    capability=next(c for c in CAPABILITIES if c['id']=='cached_viewport_geometry')
    assert capability['support']=='public_source_verified'
    assert 'not separately documented' in capability['limits']
    assert 'all rendered edge tiles' in capability['limits'] and 'cache age' in capability['limits']
