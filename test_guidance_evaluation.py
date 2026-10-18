"""Ensure evidence validation rejects well-ranked but unusable source responses."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from dev.verify_guidance import validate_result
from syx_knowledge import install_seed
from syx_mcp import Advisor


def evidence(tmp_path):
    install_seed(tmp_path)
    case=json.loads((Path(__file__).parent/'guidance-questions.json').read_text())[0]
    found=Advisor(tmp_path/'snapshot.json',tmp_path/'corpus.json').search(case['query'],'0.71.44',limit=1)
    return case, found


@pytest.mark.parametrize('mutation', ['support', 'caveat', 'url', 'authority', 'author', 'compatibility'])
def test_rejects_damaged_evidence(tmp_path, mutation):
    case, found=evidence(tmp_path)
    assert validate_result(case,found)['passed']
    damaged=deepcopy(found)
    source=damaged['results'][0]
    if mutation=='support':
        source['text']='Trade title matches, but there is no supporting passage.'
    elif mutation=='caveat':
        source['version_notes']='Verified everywhere.'
    elif mutation=='url':
        source['url']='https://example.com/unrelated'
    elif mutation=='authority':
        source['authority']='community'
    elif mutation=='author':
        source['author']='Unrelated speaker'
    else:
        source['version_compatibility']='match'
    with pytest.raises(AssertionError):
        validate_result(case,damaged)


def test_no_match_cannot_accept_unrelated_evidence(tmp_path):
    case,found=evidence(tmp_path)
    case={**case,'expected_id':None}
    with pytest.raises(AssertionError,match='unexpected evidence'):
        validate_result(case,found)
