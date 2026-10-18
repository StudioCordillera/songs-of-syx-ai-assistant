"""Local Git fixtures; no GitHub, provider, game or secret needed."""
import json
from pathlib import Path
import subprocess
import pytest
from dev.collaboration_status import inspect,changed_paths


def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.PIPE).decode().strip()


def commit(root,message):
    git(root,'add','.');git(root,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-m',message)


@pytest.fixture
def copies(tmp_path):
    remote=tmp_path/'remote.git';subprocess.run(['git','init','--bare','--initial-branch=main',str(remote)],check=True,capture_output=True)
    first=tmp_path/'first';subprocess.run(['git','clone',str(remote),str(first)],check=True,capture_output=True)
    (first/'shared.txt').write_text('baseline\n');(first/'releases').mkdir()
    (first/'releases/latest-user-test.json').write_text(json.dumps({'download_sha256':'first'}))
    commit(first,'baseline');git(first,'push','origin','main')
    second=tmp_path/'second';subprocess.run(['git','clone',str(remote),str(second)],check=True,capture_output=True)
    return first,second


def test_aligned_fetch_does_not_edit_files(copies):
    first,_=copies;r=inspect(first)
    assert r['state']=='aligned' and r['remote_fetched_this_check'] and not r['reconciliation_required']
    assert r['published_bundle_differs'] is False and git(first,'status','--porcelain')==''


def test_new_remote_release_and_dirty_overlap_are_preserved(copies):
    first,second=copies
    (second/'shared.txt').write_text('upstream\n')
    (second/'releases/latest-user-test.json').write_text(json.dumps({'download_sha256':'second'}))
    commit(second,'upstream');git(second,'push','origin','main')
    (first/'shared.txt').write_text('unpublished local work\n');before=git(first,'rev-parse','HEAD')
    r=inspect(first)
    assert r['state']=='behind' and r['behind']==1 and r['overlap_paths']==['shared.txt']
    assert r['published_bundle_differs'] and r['reconciliation_required']
    assert (first/'shared.txt').read_text()=='unpublished local work\n' and git(first,'rev-parse','HEAD')==before


def test_diverged_commits_are_not_merged(copies):
    first,second=copies
    (first/'shared.txt').write_text('local\n');commit(first,'local')
    (second/'shared.txt').write_text('remote\n');commit(second,'remote');git(second,'push','origin','main')
    r=inspect(first)
    assert r['state']=='diverged' and r['ahead']==r['behind']==1 and r['overlap_paths']==['shared.txt']
    assert git(first,'log','-1','--format=%s')=='local'


def test_cached_refs_and_fetch_failure_never_claim_freshness(copies):
    first,_=copies
    assert inspect(first,fetch=False)['remote_fetched_this_check'] is False
    git(first,'remote','set-url','origin',str(first/'nonexistent'))
    r=inspect(first)
    assert r['fetch_failed'] and not r['remote_fetched_this_check'] and r['reconciliation_required']


def test_rename_paths_and_conflicts_are_reported():
    paths,conflicts=changed_paths(b'R  destination with spaces\0original\0UU conflict\0?? new\0')
    assert paths==['conflict','destination with spaces','new','original'] and conflicts==['conflict']


def test_invalid_remote_is_rejected(copies):
    with pytest.raises(ValueError):inspect(copies[0],remote='--upload-pack=unexpected')


def test_native_environment_excludes_provider_secrets():
    from dev.run_player_chat_check import native_environment
    assert native_environment({'PATH':'bin','DEEPSEEK_API_KEY':'fixture','ANTHROPIC_AUTH_TOKEN':'fixture','OTHER_ACCESS_TOKEN':'fixture'})=={'PATH':'bin'}


def test_device_lock_refuses_a_second_fixture_and_releases(tmp_path):
    from dev.game_fixture_lock import exclusive_fixture
    with exclusive_fixture(tmp_path/'locks') as path:
        assert json.loads(path.read_text())['pid']>0 and path.stat().st_mode & 0o777==0o600
        with pytest.raises(RuntimeError,match='Another cooperating'):
            with exclusive_fixture(tmp_path/'locks'):pass
        assert path.read_text()
    assert path.read_text()==''
    with exclusive_fixture(tmp_path/'locks'):pass


def test_paid_runner_missing_key_does_not_build_or_start_game(monkeypatch):
    from types import SimpleNamespace
    from dev.run_player_chat_check import run
    monkeypatch.delenv('DEEPSEEK_API_KEY',raising=False)
    with pytest.raises(ValueError,match='Supply DEEPSEEK_API_KEY'):run(SimpleNamespace(env_file=None))


def test_paid_runner_accepts_local_literal_file_without_framework_environment(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from dev.run_player_chat_check import run
    keyfile=tmp_path/'.env';keyfile.write_text('DEEPSEEK_API_KEY=fixture-not-a-real-key\n');keyfile.chmod(0o600)
    monkeypatch.delenv('DEEPSEEK_API_KEY',raising=False)
    # Credential loading succeeds, then path validation refuses a non-fixture save before any game/provider work.
    with pytest.raises(ValueError,match='Create runtime/smoke-home'):
        run(SimpleNamespace(env_file=keyfile,save=tmp_path/'missing.save'))
