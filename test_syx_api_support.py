import pytest
from syx_api_manifest import MANIFEST
from syx_api_support import support


def test_inventory_is_public_and_source_linked():
    import hashlib
    from pathlib import Path
    source_root=Path(__file__).parent/'mod/src/main/java'
    for name,digest in MANIFEST['mod_source_sha256'].items():
        assert hashlib.sha256((source_root/name).read_bytes()).hexdigest()==digest
    members=MANIFEST['members']
    assert members and all(m['public'] for m in members)
    assert len({m['id'] for m in members})==len(members)
    assert len(MANIFEST['game_jar_sha256'])==64
    for member in members:
        if member['compiler_generated_enum']:
            assert member['source_match']=='compiler_generated_enum_member'
        else:
            assert len(member['source_candidates'])==1
            anchor=member['source_candidates'][0]
            assert anchor['line']>0 and len(anchor['source_sha256'])==64
        assert 'human_review_required' in member['documentation_status']


def test_capability_gaps_are_explicit():
    result=support('selected_room_instance')
    assert result['capabilities'][0]['support']=='unavailable'
    assert 'No public' in result['capabilities'][0]['limits']
    result=support('view.main.VIEW',limit=2)
    assert len(result['members'])==2 and result['next_offset']==2
    assert result['inventory_size']>result['member_total']
    assert all('view.main.VIEW' in member['id'] for member in result['members'])
    assert 'not establish official stability' in result['warning']

@pytest.mark.parametrize('kwargs',[{'limit':31},{'offset':-1},{'limit':True},{'query':'x'*501}])
def test_support_bounds(kwargs):
    with pytest.raises(ValueError):support(**kwargs)


def test_critical_binary_evidence_is_explicit():
    checks=MANIFEST['binary_checks']['checks']
    assert {check['id'] for check in checks}=={
        'resource_owned_definition','return_to_menu','engine_disposal_visibility','game_after_update_dispatch'}
    assert all(check['passed'] for check in checks)
    for check in checks:
        if 'normalized_disassembly_sha256' in check:
            assert len(check['normalized_disassembly_sha256'])==64


@pytest.mark.parametrize('capability,warning', [
    ('room_producer_degradation','Zero does not prove no wear'),
    ('entity_workplace_filter','Not present activity'),
    ('room_workforce_factors','not current productivity percentages'),
    ('room_service_counters','not people/day'),
    ('service_cohort_permissions','not effective individual eligibility'),
    ('city_trade_pipeline','Unavailable on battlefields'),
    ('regional_population_counters','Not a settlement census'),
])
def test_new_data_capabilities_have_evidence_and_explicit_limits(capability,warning):
    from pathlib import Path
    record=support(capability)['capabilities']
    assert len(record)==1 and record[0]['support']=='public_source_verified'
    assert warning in record[0]['limits']
    assert 'documented stable contracts' in record[0]['limits']
    source_paths={member['source_file'] for member in MANIFEST['members']}
    for reference in record[0]['references']:
        if reference.endswith('.java'):assert reference in source_paths
        else:assert (Path(__file__).parent/reference).is_file()
