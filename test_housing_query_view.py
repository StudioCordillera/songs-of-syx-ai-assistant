"""Detached housing schema/relationship tests; synthetic state is not native game evidence."""
from copy import deepcopy
import pytest
from syx_housing import build_view,SCOPE


def candidate(counts=(2,1)):
    return {'available':True,'coverage':'partial','scope':SCOPE,'data':{
        'rooms':[{'room_id':i,'kind':'ordinary_home','occupants_reported':n,
                  'occupant_roster':{'available':True,'coverage':'partial','ids':list(range(100+i*10,100+i*10+min(n,64))),
                                    'truncated':n>64}} for i,n in enumerate(counts)],
        'room_slots_scanned':10,'room_map_size':10,'scan_limit':10000,'room_scan_complete':True,
        'failed_room_reads':0,'failed_rosters':0,'truncated_rosters':sum(n>64 for n in counts),'row_limit':1000}}


def test_complete_batch_join_keys_and_detached_ownership():
    c=candidate();v=build_view(c);d=v['home_assignments']['data']
    assert d['rows']==[{'room_id':0,'resident_id':100,'roster_index':0},{'room_id':0,'resident_id':101,'roster_index':1},
                       {'room_id':1,'resident_id':110,'roster_index':0}]
    assert d['truncated'] is False and d['scanned_rooms']==2
    c['data']['rooms'][0]['occupant_roster']['ids'][0]=999
    assert v['home_records']['data']['rooms'][0]['occupant_roster']['ids'][0]==100
    v['field_definitions']['home_records']['room_id']='changed'
    assert build_view(candidate())['field_definitions']['home_records']['room_id']!='changed'


def test_relation_cap_omits_whole_home_batch_and_exact_bound_can_complete():
    d=build_view(candidate(),2)['home_assignments']['data']
    assert len(d['rows'])==2 and all(r['room_id']==0 for r in d['rows']) and d['truncated'] is True
    assert build_view(candidate(),1)['home_assignments']['data']['rows']==[]
    assert build_view(candidate((2,0)),2)['home_assignments']['data']['truncated'] is False


def test_unavailable_and_failed_rosters_do_not_invent_empty_home_truth():
    c=candidate();c['data']['rooms'][0]['occupant_roster']={'available':False,'coverage':'unavailable','ids':None}
    c['data']['failed_rosters']=1;c['data']['failed_room_reads']=2
    d=build_view(c)['home_assignments']['data']
    assert [r['room_id'] for r in d['rows']]==[1] and d['failed_rosters']==1 and d['failed_room_reads']==2
    unavailable={'available':False,'coverage':'unavailable','scope':SCOPE,'data':None,'reason':'No city'}
    v=build_view(unavailable);assert v['home_assignments']['data'] is None and v['home_records']['data'] is None


def test_source_scan_and_roster_truncation_qualify_links():
    c=candidate();c['data'].update(room_slots_scanned=5,room_scan_complete=False)
    d=build_view(c)['home_assignments']['data'];assert d['truncated'] and not d['room_scan_complete']
    c=candidate((65,));d=build_view(c)['home_assignments']['data']
    assert len(d['rows'])==64 and d['truncated'] and d['truncated_rosters']==1


@pytest.mark.parametrize('limit',[0,-1,10001,True,None,1.5])
def test_invalid_relation_budget(limit):
    with pytest.raises(ValueError):build_view(candidate(),limit)


@pytest.mark.parametrize('change',[
    lambda c:c['data']['rooms'].append(deepcopy(c['data']['rooms'][0])),
    lambda c:c['data']['rooms'][0]['occupant_roster'].update(ids=[True,1]),
    lambda c:c['data']['rooms'][0]['occupant_roster'].update(ids=[100]),
    lambda c:c['data']['rooms'][0]['occupant_roster'].update(truncated=True),
    lambda c:c['data'].update(room_scan_complete=False),
    lambda c:c['data'].update(room_slots_scanned=11),
    lambda c:c['data'].update(failed_rosters=False),
    lambda c:c['data'].update(row_limit=1),
    lambda c:c.update(available=False),
])
def test_malformed_detached_contract_is_refused(change):
    c=candidate();change(c)
    with pytest.raises(ValueError):build_view(c)


def test_reported_failures_cannot_understate_observed_unavailable_roster():
    c=candidate();c['data']['rooms'][0]['occupant_roster']={'available':False,'coverage':'unavailable','ids':None}
    with pytest.raises(ValueError,match='undercount'):build_view(c)


def test_reported_truncation_cannot_understate_observed_capped_roster():
    c=candidate((65,));c['data']['truncated_rosters']=0
    with pytest.raises(ValueError,match='undercount'):build_view(c)


def test_oversized_detached_view_is_refused():
    c=candidate();c['data']['rooms'][0]['extra']='x'*(2*1024*1024)
    with pytest.raises(ValueError,match='byte budget'):build_view(c)
