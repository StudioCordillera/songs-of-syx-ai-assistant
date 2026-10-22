"""Offline path admission for the fixed developer restart runner; no game or inference."""
from pathlib import Path
import pytest
from dev.run_read_fixture import layout_preferences_directory


def test_private_runtime_preferences_admission(tmp_path):
    directory = tmp_path / 'private'
    directory.mkdir(mode=0o700)
    assert layout_preferences_directory('layout-background', directory, tmp_path) == directory
    assert layout_preferences_directory('layout-background', None, tmp_path) is None
    with pytest.raises(ValueError):
        layout_preferences_directory('tiles', directory, tmp_path)


@pytest.mark.parametrize('kind', ['runtime_root', 'outside', 'symlink', 'public', 'missing', 'file'])
def test_restart_refuses_nonprivate_or_external_preferences(tmp_path, kind):
    runtime = tmp_path / 'runtime'
    runtime.mkdir(mode=0o700)
    private = runtime / 'private'
    private.mkdir(mode=0o700)
    if kind == 'runtime_root':
        candidate = runtime
    elif kind == 'outside':
        candidate = tmp_path / 'outside'
        candidate.mkdir(mode=0o700)
    elif kind == 'symlink':
        candidate = runtime / 'link'
        candidate.symlink_to(private, target_is_directory=True)
    elif kind == 'public':
        candidate = runtime / 'public'
        candidate.mkdir(mode=0o755)
        candidate.chmod(0o755)  # Keep the negative shape independent of the caller's umask.
    elif kind == 'missing':
        candidate = runtime / 'missing'
    else:
        candidate = runtime / 'file'
        candidate.write_text('preserve')
    with pytest.raises((ValueError, FileNotFoundError)):
        layout_preferences_directory('layout-background', candidate, runtime)
