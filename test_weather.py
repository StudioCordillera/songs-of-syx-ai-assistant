"""Weather is scoped observation data: legitimate zero and cached flags are not missing values."""
import pytest
from syx_query import QueryEngine
from test_syx_query import snapshot
from syx_api_support import CAPABILITIES


def test_weather_same_observation_projection_keeps_zero_and_independent_flags(snapshot):
    snapshot.domains['map'].coverage='partial'
    snapshot.domains['map'].data={'weather':{'coverage':'partial','scope':'instantiated_city_weather','data':{
        'factors':{'wind_strength':0,'seasonal_ripeness':.9},'flags':{'crops_ripe':True}}}}
    result=QueryEngine(snapshot).execute({'expected_snapshot_id':snapshot.snapshot_id,'queries':[{
        'source':{'domain':'map','path':'/weather/data'},'select':{'wind':{'field':'/factors/wind_strength'},
        'ripe':{'field':'/flags/crops_ripe'},'seasonal':{'field':'/factors/seasonal_ripeness'}}}]})[0]
    assert result['rows']==[{'wind':0,'ripe':True,'seasonal':.9}]


def test_weather_unavailable_is_not_empty_or_zero(snapshot):
    snapshot.domains['map'].coverage='partial'
    snapshot.domains['map'].data={'weather':{'coverage':'unavailable','scope':'instantiated_city_weather','data':None,'reason':'No completed city'}}
    with pytest.raises(ValueError,match='Requested observation is unavailable'):
        QueryEngine(snapshot).execute({'queries':[{'source':{'domain':'map','path':'/weather/data'},'aggregates':{'n':{'op':'count'}}}]})


def test_weather_capability_distinguishes_stored_scale_and_documented_contract():
    c=next(c for c in CAPABILITIES if c['id']=='stored_city_weather')
    assert c['support']=='public_source_verified' and 'not documented stable contracts' in c['limits']
    assert 'prior stored factor' in c['limits'] and 'not' in c['limits'].lower()
