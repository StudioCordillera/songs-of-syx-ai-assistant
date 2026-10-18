"""A new licensed pair or missing public route must invalidate candidate review."""
import hashlib
import json
from pathlib import Path
import pytest
from dev.review_regional_output_boundary import check_pair,review


def inputs(tmp_path):
    (tmp_path/'info').mkdir()
    (tmp_path/'SongsOfSyx.jar').write_bytes(b'fixture binary')
    (tmp_path/'info/SongsOfSyx-sources.jar').write_bytes(b'fixture source')
    catalog=tmp_path/'catalog.json'
    catalog.write_text(json.dumps({'game_jar_sha256':hashlib.sha256(b'fixture binary').hexdigest(),
        'source_archive_sha256':hashlib.sha256(b'fixture source').hexdigest(),'members':[]}))
    return catalog


@pytest.mark.parametrize('changed',['SongsOfSyx.jar','info/SongsOfSyx-sources.jar'])
def test_regional_review_rejects_changed_licensed_pair_before_java(tmp_path,changed):
    catalog=inputs(tmp_path);(tmp_path/changed).write_bytes(b'a different installed build')
    with pytest.raises(ValueError,match='differs from licensed'):
        check_pair(tmp_path,catalog)


def test_missing_candidate_public_route_is_refused_before_compilation(tmp_path):
    catalog=inputs(tmp_path)
    with pytest.raises(ValueError,match='public declaration missing'):
        review(tmp_path,Path('unused java home'),catalog)
