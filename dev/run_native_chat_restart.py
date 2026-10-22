"""Two sequential copied-game JVMs share only private candidate layout preferences.

No normal profile/config, credentials, real inference, screenshots or native input.
The shared native fixture lock is held for both launches; helpers/histories remain separate.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / 'dev')]
from game_fixture_lock import exclusive_fixture
from run_read_fixture import run, sha

SOURCES = ['dev/run_native_chat_restart.py', 'dev/run_read_fixture.py', 'dev/verify_native_chat_background.py',
    'dev/candidates/chat-layout/ChatPanel.java', 'dev/candidates/chat-layout/ChatBackgroundScenario.java',
    'dev/java/syx/assistant/candidate/PanelPreferences.java', 'dev/java/syx/assistant/candidate/PanelTheme.java',
    'dev/java/syx/assistant/candidate/GestureReducer.java']


def preference_fields(path):
    raw = path.read_bytes()
    assert len(raw) <= 512 and raw.startswith(b'version=2\n')
    fields = dict(line.split('=', 1) for line in raw.decode('ascii').splitlines())
    assert set(fields) == {'version', 'panel_x', 'panel_y', 'panel_width', 'panel_height',
                          'launcher_x', 'launcher_y', 'launcher_width', 'launcher_height', 'preset', 'accent'}
    return fields


def verify_restoration(first, second, saved):
    for report in (first, second):
        assert report['passed'] and report['game_exit_code'] == 0
        assert report['copied_profile_mod_restored'] and report['copied_save_unchanged']
        assert report['explicit_fixture_clean_completion'] and report['known_engine_crash_markers_absent']
        native = report['native_checks']
        assert len(native['checks']) == 7 and all(c['passed'] for c in native['checks'])
        assert native['initial_layout']['preferences_configured'] is True
        assert report['completed_turns'] == report['cancelled_turns'] == 1
        assert report['external_inference_calls'] == 0
    initial = first['native_checks']['initial_layout']
    assert initial['preset'] == 'Forest' and initial['panel']['width'] == 840 and initial['panel']['height'] == 640
    restored = second['native_checks']['initial_layout']
    assert restored['preset'] == saved['preset'] == 'Parchment'
    assert restored['accent'] == saved['accent'] == '#745137'
    for kind in ('panel', 'launcher'):
        assert restored[kind] == {key: int(saved[kind + '_' + key]) for key in ('x', 'y', 'width', 'height')}
    assert restored['panel']['width'] == 880 and restored['panel']['height'] == 660
    for key in ('mod_jar_sha256', 'game_jar_sha256', 'source_archive_sha256', 'compiled_fixture_source_sha256'):
        assert first[key] == second[key]


def main(args):
    hashes = {n: sha(ROOT / n) for n in SOURCES}
    root = Path(tempfile.mkdtemp(prefix='native-chat-restart-', dir=ROOT / 'runtime')).resolve()
    os.chmod(root, 0o700)
    preferences = root / 'preferences'
    preferences.mkdir(mode=0o700)
    args.case = 'layout-background'
    args.env_file = None
    args.layout_preferences_dir = preferences
    with exclusive_fixture():
        first_path = run(args)
        saved = preference_fields(preferences / 'chat-layout.preferences')
        saved_sha = sha(preferences / 'chat-layout.preferences')
        second_path = run(args)
    first, second = (json.loads(p.read_text()) for p in (first_path, second_path))
    verify_restoration(first, second, saved)
    assert hashes == {n: sha(ROOT / n) for n in SOURCES}
    report = {'passed': True, 'evaluated_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'Developer candidate preference startup across two actual sequential copied-game JVMs, with separate production-helper/MCP/history paths and fake inference.',
        'source_sha256': hashes, 'native_game_launches': 2, 'native_phase_checks': 14,
        'shared_private_assistant_preferences_only': True, 'normal_player_configuration_accessed': False,
        'first_saved_preferences_sha256': saved_sha,
        'second_constructor_restored_first_saved_geometry_and_style': True,
        'production_integrated': False, 'external_inference_calls': 0,
        'runs': [{'private_native_report_sha256': sha(path), **data} for path, data in ((first_path, first), (second_path, second))],
        'limits': ['Only an explicit developer startup property points our candidate at a runner-created mode-0700 runtime subdirectory; no automatic production preference path is selected.',
            'Each game uses the same copied save/profile sequentially under the shared fixture lock. Each has separate assistant helper state/history; only the assistant preference directory is shared, alongside the intentionally common copied game/profile. No permanent world identity or same-history reconnect/recovery is attested.',
            'Fake provider only. Own supplied launcher/resize gestures and public own controls are not physical/native input, screenshots, focus/pixel/accessibility/receipt acceptance or gameplay commands.',
            'Two clean launches/restorations do not establish crash/power-loss, concurrent-game, alternate-resolution or every-load acceptance. Production JAR and both tested bundles remain unchanged.']}
    output = root / 'native-chat-restart-validation.json'
    output.write_text(json.dumps(report, indent=2) + '\n')
    print('Native chat restart passed:', output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('game-dir', 'jdk-home', 'java', 'save'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--candidate-dir', type=Path)
    parser.add_argument('--validation', type=Path)
    main(parser.parse_args())
