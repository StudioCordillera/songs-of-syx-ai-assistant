"""Original teaching geometry and truthful catalog-only evidence; no game, inference or placement."""
import hashlib
import json
from pathlib import Path
import pytest
from dev.blueprint_examples import BlueprintRegistry,load_registry

ROOT=Path(__file__).resolve().parent
ID='warehouse-two-items-teaching-grid'

def inputs():
    return json.loads((ROOT/'blueprint-examples-candidate.json').read_text()),(ROOT/'BLUEPRINT_CATALOG_VALIDATION.json').read_bytes()
def build(data,report):return BlueprintRegistry(json.dumps(data).encode(),report)

def test_original_example_has_exact_authored_geometry_and_explicit_non_execution():
    r=load_registry();v=r.get(ID,'0.71.44')
    assert v['geometry']['grid']==['.....','.RF..','E....','.RF..','.....']
    assert v['geometry']['furniture_footprint_cells']==4 and v['geometry']['item_instances']==2
    assert v['geometry']['geometrically_connected_nonblocked_cells']==21
    assert v['construction_validated'] is v['execution_supported'] is False
    assert v['compatibility']=='exact_catalog_version_only'
    assert v['catalog_item']['must_be_indoors'] is True
    assert 'storage capacity' in v['limits'][0]
    assert v['example']['origin']=='original_project_schematic'

def test_search_is_bounded_discovery_and_does_not_dump_geometry():
    r=load_registry();hits=r.search('warehouse aisle','0.71.44')
    assert len(hits)==1 and hits[0]['id']==ID and hits[0]['geometry_included'] is False
    assert 'geometry' not in hits[0] and r.search('unrelated astronomy','0.71.44')==[]
    assert r.search('warehouse','0.72.0')[0]['compatibility']=='unknown'
    assert r.get(ID,'0.72.0')['compatibility']=='unknown'

def test_returned_records_geometry_catalog_and_search_are_owned_copies():
    r=load_registry();a=r.get(ID,'0.71.44');a['geometry']['grid'][0]='bad';a['example']['placements'].clear();a['catalog_item']['cells'].clear()
    hits=r.search('warehouse','0.71.44');hits[0]['title']='bad'
    assert r.get(ID,'0.71.44')['geometry']['grid'][0]=='.....'
    assert len(r.get(ID,'0.71.44')['catalog_item']['cells'])==2
    assert r.search('warehouse','0.71.44')[0]['title']!='bad'

@pytest.mark.parametrize('change',['checksum','duplicate','identity','outside','overlap','entry','disconnected','access','unknown_action','bool_dimension','oversize','external_origin','bool_schema'])
def test_malformed_identity_geometry_and_unreviewed_features_refuse(change):
    d,report=inputs();e=d['examples'][0]
    if change=='bool_schema':d['schema_version']=True
    elif change=='checksum':d['catalog_report_sha256']='0'*64
    elif change=='duplicate':d['examples'].append(dict(e))
    elif change=='identity':e['catalog_item_index']+=1
    elif change=='outside':e['placements'][0]={'x':4,'y':1}
    elif change=='overlap':e['placements'][1]=dict(e['placements'][0])
    elif change=='entry':e['entry']={'x':2,'y':2}
    elif change=='disconnected':e.update(width=2,height=3,entry={'x':0,'y':0},placements=[{'x':0,'y':1}])
    elif change=='access':e.update(width=4,height=3,entry={'x':0,'y':0},placements=[{'x':0,'y':1},{'x':2,'y':1},{'x':0,'y':2},{'x':2,'y':2}])
    elif change=='unknown_action':e['execute']={'method':'build'}
    elif change=='bool_dimension':e['width']=True
    elif change=='oversize':e['width']=65
    elif change=='external_origin':e['origin']='youtube_frame_inferred'
    with pytest.raises(ValueError):build(d,report)

@pytest.mark.parametrize('change',['bad_footprint','no_clean_exit','wrong_version','failed_restoration'])
def test_even_rehashed_evidence_requires_selected_catalog_contract(change):
    d,raw=inputs();report=json.loads(raw)
    if change=='bad_footprint':report['catalog_item']['cells'][0]['must_be_reachable']=False
    elif change=='no_clean_exit':report['game_exit_code']=1
    elif change=='wrong_version':report['game_version']='0.72.0'
    elif change=='failed_restoration':report['copied_profile_mod_restored']=False
    raw=json.dumps(report).encode();d['catalog_report_sha256']=hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError):build(d,raw)

def test_byte_budget_and_query_arguments_refuse():
    d,report=inputs()
    with pytest.raises(ValueError):BlueprintRegistry(b' '*131073,report)
    r=build(d,report)
    for query,limit in [('',1),('a'*301,1),('warehouse',True),('warehouse',11)]:
        with pytest.raises(ValueError):r.search(query,'0.71.44',limit)
    for version in [None,'current','0.72',True]:
        with pytest.raises(ValueError):r.get(ID,version)
    with pytest.raises(ValueError):r.get('unknown','0.71.44')


@pytest.mark.parametrize('bad',[b'{"schema_version":1,"schema_version":1}',b'{"x":NaN}'])
def test_ambiguous_or_nonfinite_json_refuses(bad):
    _,report=inputs()
    with pytest.raises(ValueError):BlueprintRegistry(bad,report)

@pytest.mark.parametrize('field,value',[('height',True),('size',False),('rotation',False),('item_index',True)])
def test_boolean_catalog_numbers_refuse_even_after_rehash(field,value):
    d,raw=inputs();report=json.loads(raw);report['catalog_item'][field]=value
    raw=json.dumps(report).encode();d['catalog_report_sha256']=hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError):build(d,raw)
