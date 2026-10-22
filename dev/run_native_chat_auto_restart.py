"""Two sequential copied-game JVMs retain one automatic preference file in place.

Only own disposable fixture outputs are archived between launches. Shared lock,
no preference override, no credentials, real model, screenshots or native input.
"""
import argparse
from datetime import datetime, timezone
import itertools
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / 'dev')]
from game_fixture_lock import exclusive_fixture
from run_read_fixture import run, sha, layout_preferences_directory, layout_shared_state_directory
from run_native_chat_restart import preference_fields, verify_restoration, SOURCES as PREVIOUS_SOURCES

SOURCES = sorted(set(PREVIOUS_SOURCES + ['dev/run_native_chat_auto_restart.py',
    'dev/java/syx/assistant/candidate/StatusLines.java']))


def archive_fixture_outputs(state, runtime):
    """Preserve all own artifacts without moving/copying/rewriting the preference file."""
    state = layout_preferences_directory('layout-background', state, runtime)
    archive = state.parent / (state.name + '-first-run')
    if archive.exists() or archive.is_symlink():
        raise ValueError('First-run archive already exists; preserve it')
    preference = state / 'chat-layout.preferences'
    if preference.is_symlink() or not preference.is_file():
        raise ValueError('Regular own preference file required')
    info = preference.stat()
    before = (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_mode, sha(preference))
    with os.scandir(state) as entries:
        selected = list(itertools.islice(entries, 129))
    if len(selected) > 128 or any(e.is_symlink() for e in selected):
        raise ValueError('Bounded regular own fixture artifacts required')
    archive.mkdir(mode=0o700)
    for entry in selected:
        if entry.name != 'chat-layout.preferences':
            Path(entry.path).rename(archive / entry.name)
    after = preference.stat()
    assert (after.st_dev, after.st_ino, after.st_mtime_ns, after.st_mode, sha(preference)) == before
    assert layout_shared_state_directory('layout-background', state, runtime) == state
    return archive


def main(args):
    hashes = {n: sha(ROOT / n) for n in SOURCES}
    root = Path(tempfile.mkdtemp(prefix='native-chat-auto-restart-', dir=ROOT / 'runtime')).resolve()
    os.chmod(root, 0o700)
    # LiveSmoke deliberately requires state roots directly below runtime so its
    # copied-profile guard remains intact. Do not weaken that Java boundary.
    state = Path(tempfile.mkdtemp(prefix='read-auto-shared-', dir=ROOT / 'runtime')).resolve()
    os.chmod(state, 0o700)
    args.case = 'layout-background'
    args.env_file = None
    args.layout_preferences_dir = None
    args.layout_shared_state_dir = state
    with exclusive_fixture():
        first_path = run(args)
        saved = preference_fields(state / 'chat-layout.preferences')
        saved_sha = sha(state / 'chat-layout.preferences')
        archive = archive_fixture_outputs(state, ROOT / 'runtime')
        first_path = archive / first_path.name
        assert sha(state / 'chat-layout.preferences') == saved_sha
        second_path = run(args)
    first, second = (json.loads(p.read_text()) for p in (first_path, second_path))
    verify_restoration(first, second, saved)
    assert all(v['native_checks']['initial_layout']['automatic_preferences_selected'] for v in (first, second))
    assert hashes == {n: sha(ROOT / n) for n in SOURCES}
    report = {'passed': True, 'evaluated_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'Developer automatic preference startup across two actual copied-game JVMs sharing the same assistant state root and retained preference inode; fake inference only.',
        'source_sha256': hashes, 'native_game_launches': 2, 'native_phase_checks': 14,
        'same_state_root_and_preference_inode_retained_between_launches': True,
        'all_other_first_run_fixture_artifacts_preserved_in_archive': True,
        'explicit_preference_property_supplied': False, 'normal_assistant_preference_root_selected': False,
        'first_saved_preferences_sha256': saved_sha,
        'second_constructor_automatically_restored_first_saved_geometry_and_style': True,
        'production_integrated': False, 'external_inference_calls': 0,
        'runs': [{'private_native_report_sha256': sha(path), **data} for path, data in ((first_path, first), (second_path, second))],
        'limits': ['Same private mode-0700 assistant state directory and unchanged mode-0600 preference file stay in place between launches. No preference copy, migration or developer directory override.',
            'Only other fixed disposable fixture outputs/history/IPC/markers/classes are moved to a private first-run archive after the first runner completes. New helper/history per launch; no same-history or provider continuation claim.',
            'Copied game/profile/save are intentionally common, sequential and under one shared fixture lock. No normal configuration root, permanent world identity, credential or explicit save is selected.',
            'Two finite native startups with fake providers and own supplied gestures/public own controls; no physical input, screenshots, pixel/readability/accessibility/receipt or paid acceptance.',
            'No concurrent-game, crash/power-loss, hostile filesystem-race, all-resolution/load or player-release acceptance. Production source/current/previous player ZIPs unchanged.']}
    output = root / 'native-chat-auto-restart-validation.json'
    output.write_text(json.dumps(report, indent=2) + '\n')
    print('Native automatic preference restart passed:', output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('game-dir', 'jdk-home', 'java', 'save'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--candidate-dir', type=Path)
    parser.add_argument('--validation', type=Path)
    main(parser.parse_args())
