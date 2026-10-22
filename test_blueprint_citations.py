"""Immutable original-reference locators, distinct from live/version compatibility."""
import hashlib
import json
from pathlib import Path

import pytest

from dev.blueprint_examples import BlueprintRegistry, SOURCE_COMMIT, SOURCE_FILES, load_registry

ROOT = Path(__file__).resolve().parent
EXAMPLE = 'warehouse-two-items-teaching-grid'


def test_search_and_get_share_exact_published_artifact_citations_without_geometry_dump():
    registry = load_registry()
    hit = registry.search('warehouse', '0.71.44')[0]
    fetched = registry.get(EXAMPLE, '0.71.44')
    citation = hit['citation']
    assert citation == fetched['citation']
    assert citation['status'] == 'exact_reviewed_artifacts'
    assert citation['source_commit'] == SOURCE_COMMIT
    assert '/main/' in hit['source_url'] and 'navigation only' in citation['limit']
    assert len(citation['artifacts']) == 3
    for artifact in citation['artifacts']:
        assert artifact['url'].split('/blob/')[1] == SOURCE_COMMIT + '/' + artifact['path']
        assert artifact['sha256'] == SOURCE_FILES[artifact['path']]
        if artifact['path'].endswith('.json'):
            assert hashlib.sha256((ROOT / artifact['path']).read_bytes()).hexdigest() == artifact['sha256']
    assert 'geometry' not in hit
    assert fetched['construction_validated'] is fetched['execution_supported'] is False


@pytest.mark.parametrize('change', ['corpus_text', 'corpus_whitespace', 'report_date'])
def test_modified_even_semantically_valid_inputs_do_not_inherit_published_citations(change):
    corpus_bytes = (ROOT / 'blueprint-examples-candidate.json').read_bytes()
    report_bytes = (ROOT / 'BLUEPRINT_CATALOG_VALIDATION.json').read_bytes()
    corpus = json.loads(corpus_bytes)
    if change == 'corpus_text':
        corpus['examples'][0]['summary'] = 'Locally changed teaching summary'
        corpus_bytes = json.dumps(corpus).encode()
    elif change == 'corpus_whitespace':
        corpus_bytes += b'\n'
    else:
        report = json.loads(report_bytes)
        report['evaluated_at'] = '2000-01-01T00:00:00Z'
        report_bytes = json.dumps(report).encode()
        corpus['catalog_report_sha256'] = hashlib.sha256(report_bytes).hexdigest()
        corpus_bytes = json.dumps(corpus).encode()
    registry = BlueprintRegistry(corpus_bytes, report_bytes)
    for citation in [registry.citation(), registry.search('warehouse', '0.71.44')[0]['citation'],
                     registry.get(EXAMPLE, '0.71.44')['citation']]:
        assert citation['status'] == 'unverified_modified_artifacts'
        assert citation['artifacts'] == []
        assert 'source_commit' not in citation


def test_other_version_retains_original_citation_without_upgrading_compatibility():
    fetched = load_registry().get(EXAMPLE, '0.72.0')
    assert fetched['compatibility'] == 'unknown'
    assert fetched['example']['game_version'] == '0.71.44'
    assert fetched['citation']['status'] == 'exact_reviewed_artifacts'
    assert 'not current installation' in fetched['citation']['limit']


def test_citations_are_owned_copies_in_all_public_results():
    registry = load_registry()
    for citation in [registry.citation(), registry.search('warehouse', '0.71.44')[0]['citation'],
                     registry.get(EXAMPLE, '0.71.44')['citation']]:
        citation['artifacts'][0]['url'] = 'changed'
        citation['artifacts'].clear()
    assert len(registry.citation()['artifacts']) == 3
    assert len(SOURCE_FILES) == 3
