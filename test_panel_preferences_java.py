"""Detached Java preference validation/filesystem ownership; no game or provider."""
import os
from pathlib import Path
import subprocess


def test_bounded_private_panel_preferences_and_atomic_ownership(tmp_path):
    root = Path(__file__).resolve().parent
    classes = tmp_path / 'classes'
    classes.mkdir()
    compiler = ['java']
    if os.environ.get('SYX_JAVA_HOME'):
        compiler += ['-Djava.home=' + os.environ['SYX_JAVA_HOME']]
    sources = [root / 'dev/java/syx/assistant/candidate' / name for name in
               ['GestureReducer.java', 'PanelTheme.java', 'PanelPreferences.java', 'PanelPreferencesProbe.java']]
    subprocess.run([*compiler, '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '16',
                    '-d', str(classes), *map(str, sources)], check=True, capture_output=True, timeout=30)
    directory = tmp_path / 'preferences'
    directory.mkdir()
    result = subprocess.run(['java', '-cp', str(classes), 'syx.assistant.candidate.PanelPreferencesProbe', str(directory)],
                            check=True, capture_output=True, text=True, timeout=30)
    assert result.stdout.splitlines() == ['exact_roundtrip', 'unknown_version', 'duplicate_fields',
        'unknown_fields', 'missing_fields', 'invalid_bounded_integers', 'zero_dimensions',
        'ascii_lines_and_byte_bound', 'version_two_roundtrip', 'version_two_style_refusal', 'legacy_load_no_rewrite', 'missing_file_defaults', 'private_atomic_save',
        'replace_and_fresh_load', 'oversized_file_preserved', 'directory_file_refused',
        'symlink_load_save_refused', 'symlink_directory_refused',
        'atomic_replace_preserves_other_hardlink', 'no_temporary_files_left']


def test_version_two_geometry_and_style_survive_a_separate_jvm(tmp_path):
    root = Path(__file__).resolve().parent
    classes = tmp_path / 'classes'
    classes.mkdir()
    compiler = ['java']
    if os.environ.get('SYX_JAVA_HOME'):
        compiler += ['-Djava.home=' + os.environ['SYX_JAVA_HOME']]
    sources = [root / 'dev/java/syx/assistant/candidate' / name for name in
               ['GestureReducer.java', 'PanelTheme.java', 'PanelPreferences.java', 'PanelPreferencesProbe.java']]
    subprocess.run([*compiler, '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '16',
                    '-d', str(classes), *map(str, sources)], check=True, capture_output=True, timeout=30)
    directory = tmp_path / 'preferences'
    directory.mkdir()
    for mode in ['write-v2', 'read-v2']:
        result = subprocess.run(['java', '-cp', str(classes), 'syx.assistant.candidate.PanelPreferencesProbe', str(directory), mode],
                                check=True, capture_output=True, text=True, timeout=30)
        assert result.stdout.strip() == 'PASS ' + mode
