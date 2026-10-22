"""Disposable shared-state admission and recoverable artifact preservation."""
import pytest
from dev.run_read_fixture import layout_shared_state_directory
from dev.run_native_chat_auto_restart import archive_fixture_outputs


def test_shared_root_accepts_empty_then_only_private_preferences(tmp_path):
    state = tmp_path / 'state'
    state.mkdir(mode=0o700)
    assert layout_shared_state_directory('layout-background', state, tmp_path) == state
    preference = state / 'chat-layout.preferences'
    preference.write_text('version=2\n')
    preference.chmod(0o600)
    assert layout_shared_state_directory('layout-background', state, tmp_path) == state
    assert layout_shared_state_directory('layout-background', None, tmp_path) is None


@pytest.mark.parametrize('shape', ['wrong_case', 'unknown_file', 'preference_link', 'public_preference', 'preference_directory'])
def test_shared_state_refuses_unsafe_or_unarchived_shapes(tmp_path, shape):
    state = tmp_path / 'state'
    state.mkdir(mode=0o700)
    file = state / 'chat-layout.preferences'
    if shape == 'wrong_case':
        case = 'layout-notices'
    else:
        case = 'layout-background'
        if shape == 'unknown_file':
            (state / 'history.sqlite3').write_text('preserve')
        elif shape == 'preference_link':
            file.symlink_to(tmp_path / 'outside')
        elif shape == 'public_preference':
            file.write_text('preserve')
            file.chmod(0o644)
        else:
            file.mkdir()
    with pytest.raises(ValueError):
        layout_shared_state_directory(case, state, tmp_path)


def test_archive_retains_same_preference_inode_and_every_other_artifact(tmp_path):
    state = tmp_path / 'state'
    state.mkdir(mode=0o700)
    preference = state / 'chat-layout.preferences'
    preference.write_text('version=2\n')
    preference.chmod(0o600)
    before = preference.stat()
    (state / 'read-validation.json').write_text('private fixture report')
    (state / 'history').mkdir()
    (state / 'history' / 'data').write_text('private fixture history')
    archive = archive_fixture_outputs(state, tmp_path)
    assert list(state.iterdir()) == [preference]
    assert (preference.stat().st_ino, preference.stat().st_mtime_ns) == (before.st_ino, before.st_mtime_ns)
    assert (archive / 'read-validation.json').read_text() == 'private fixture report'
    assert (archive / 'history' / 'data').read_text() == 'private fixture history'
    with pytest.raises(ValueError, match='already exists'):
        archive_fixture_outputs(state, tmp_path)
