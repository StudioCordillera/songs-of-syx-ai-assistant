"""A different licensed build must not inherit a previous stockpile semantic review."""
import hashlib
import json
import pytest
from dev.run_stockpile_probe import check_game_pair


def test_stockpile_probe_pins_both_game_and_source_before_native_run(tmp_path):
    (tmp_path/'info').mkdir()
    (tmp_path/'SongsOfSyx.jar').write_bytes(b'synthetic jar fixture')
    (tmp_path/'info/SongsOfSyx-sources.jar').write_bytes(b'synthetic source fixture')
    review=tmp_path/'review.json'
    values={'passed':True,'game_jar_sha256':hashlib.sha256(b'synthetic jar fixture').hexdigest(),
        'source_archive_sha256':hashlib.sha256(b'synthetic source fixture').hexdigest()}
    review.write_text(json.dumps(values))
    checked=check_game_pair(tmp_path,review)
    assert all(checked[k]==v for k,v in values.items() if k!='passed')
    (tmp_path/'info/SongsOfSyx-sources.jar').write_bytes(b'changed source fixture')
    with pytest.raises(ValueError,match='differs from the static'):
        check_game_pair(tmp_path,review)


def test_stockpile_probe_refuses_failed_static_review_even_when_hashes_match(tmp_path):
    (tmp_path/'info').mkdir()
    for name in ['SongsOfSyx.jar','info/SongsOfSyx-sources.jar']:(tmp_path/name).write_bytes(b'fixture')
    digest=hashlib.sha256(b'fixture').hexdigest()
    review=tmp_path/'review.json'
    review.write_text(json.dumps({'passed':False,'game_jar_sha256':digest,'source_archive_sha256':digest}))
    with pytest.raises(ValueError,match='differs from the static'):
        check_game_pair(tmp_path,review)
