"""Static reviews must fail closed on changed routes and unrelated compiler failures."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from dev.review_ui_lifecycle_boundary import reader,compile_probe,review


@pytest.mark.parametrize('changed',[
    '  1: putfield #1 // current',
    '  1: anewarray #1',
    '  1: invokedynamic #1',
    '  9: goto 0',
])
def test_candidate_reader_rejects_mutation_allocation_dispatch_or_loop(changed):
    with pytest.raises(ValueError):reader('  0: getfield #1 // stored\n'+changed,['stored'])


def test_reader_requires_reviewed_semantic_marker():
    with pytest.raises(ValueError,match='route changed'):reader('  0: ireturn',['panel_identity'])


def test_negative_probe_does_not_accept_unrelated_compiler_error(tmp_path,monkeypatch):
    import dev.review_ui_lifecycle_boundary as checker
    monkeypatch.setattr(checker.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=1,stderr='compiler.err.cant.resolve'))
    with pytest.raises(ValueError,match='restriction changed'):
        compile_probe(['java'],Path('not-loaded.jar'),tmp_path,'Access','Object x;',
            'compiler.err.report.access')


def test_ui_review_refuses_different_source_pair_before_invocation(tmp_path):
    (tmp_path/'info').mkdir();(tmp_path/'SongsOfSyx.jar').write_bytes(b'jar')
    (tmp_path/'info/SongsOfSyx-sources.jar').write_bytes(b'changed source')
    catalog=tmp_path/'catalog.json';catalog.write_text(json.dumps({
        'game_jar_sha256':hashlib.sha256(b'jar').hexdigest(),
        'source_archive_sha256':hashlib.sha256(b'original source').hexdigest()}))
    with pytest.raises(ValueError,match='differs from licensed'):
        review(tmp_path,Path('unused jdk'),catalog)
