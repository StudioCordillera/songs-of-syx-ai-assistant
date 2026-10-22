"""Developer overlay of our ChatPanel: native bounds, drafts, own gestures and synthetic IPC.

No provider, normal history/profile, screenshots or engine/native input injection.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / 'dev')]
from game_fixture_lock import exclusive_fixture
from run_stockpile_probe import run, sha

SOURCES = ['dev/run_native_chat_layout.py', 'dev/run_stockpile_probe.py',
    'dev/candidates/chat-layout/ChatPanel.java', 'dev/candidates/chat-layout/ChatLayoutProbe.java',
    'dev/candidates/chat-layout/StockpileScenario.java', 'dev/java/syx/assistant/candidate/GestureReducer.java', 'dev/java/syx/assistant/candidate/PanelPreferences.java', 'dev/java/syx/assistant/candidate/PanelTheme.java', 'dev/java/syx/assistant/candidate/StatusLines.java',
    'mod/src/main/java/syx/assistant/ChatPanel.java', 'mod/tests/LiveSmoke.java', 'dev/native_game_completion.py']
GAME_PATHS = ['snake2d/Mouse.java', 'snake2d/MButt.java', 'snake2d/util/gui/clickable/CLICKABLE.java',
    'snake2d/util/gui/GuiSection.java', 'util/gui/misc/GInput.java', 'util/gui/table/GScrollRows.java',
    'snake2d/util/sprite/text/StringInputSprite.java', 'view/interrupter/InterGuisection.java',
    'snake2d/util/color/ColorImp.java', 'snake2d/util/color/COLOR.java', 'util/gui/misc/GText.java', 'util/gui/misc/GTextR.java',
    'view/interrupter/Interrupter.java', 'view/interrupter/InterManager.java', 'view/main/VIEW.java']
CHECKS = {'header_drag_and_heartbeat_stability', 'responsive_minimum_controls_and_draft',
    'content_refuses_capture', 'normal_send_protocol', 'normal_stop_protocol',
    'reopen_retains_transcript_and_chat', 'explicit_layout_reset', 'manager_deactivation_cancel',
    'scene_change_cancel', 'hidden_ui_cancel', 'idle_viewport_reflow_and_draft',
    'viewport_change_cancels_capture', 'undersized_viewport_closes_and_releases_own_focus',
    'viewport_recovery_and_closed_launcher_bounds', 'explicit_preferences_save_reload',
    'automatic_clamp_does_not_write_preferences', 'malformed_preferences_preserve_layout_and_explicit_reset',
    'appearance_presets_minimum_bounds_and_draft', 'custom_accent_validation_and_focus_ownership', 'explicit_style_persistence_and_fresh_panel_reload',
    'legacy_geometry_no_rewrite_until_explicit_style','wrapped_status_minimum_bounds_and_scroll','automatic_state_directory_preferences'}


async def verify(state, manifest):
    for name, digest in SOURCE_HASHES.items():
        assert sha(ROOT / name) == digest, 'Candidate source changed during the native fixture'
    raw = json.loads((state / 'stockpile-fixture.json').read_text())
    assert raw['passed'] and set(raw['checks']) == CHECKS and len(raw['checks']) == len(CHECKS)
    assert raw['composer_capacity'] == 240 and raw['handle_render_callbacks'] > 0
    assert raw['engine_viewport_changed'] is False
    assert raw['supplied_layout_viewports'] == [[700, 600], [680, 580], [600, 500], [100, 60]]
    assert raw['provider_calls'] == 0 and raw['synthetic_protocol_frames'] is True
    return {'passed': True, 'evaluated_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'Developer-only own ChatPanel class overlay with real controls/layout and synthetic helper frames; supplied gesture primitives, not physical input or a player release.',
        'native_checks': raw, 'source_sha256': SOURCE_HASHES, 'selected_game_source_sha256': GAME_HASHES,
        'base_player_mod_jar_sha256': manifest['mod_jar_sha256'],
        'base_production_source_sha256': manifest['validation']['production_source_sha256'],
        'base_python_source_sha256': manifest['validation']['python_source_sha256'],
        'our_chat_class_overlaid_from_fixture_classes': True, 'engine_classes_overridden': False,
        'provider_calls': 0, 'native_input_injections': 0, 'production_integrated': False,
        'limits': ['One copied paused city and reported internal native viewport, with fixed test-only world/hidden presentation phases. No natural unpaused/focus/all-menu/scale acceptance.',
            'Our own candidate ChatPanel substitutes the base class only in this fixture classpath. Engine/tutorial JARs precede the fixture classes. The tested player JAR/ZIP and normal profile remain unchanged.',
            'Launcher/header/resize capture is driven by supplied owned primitives. Normal Close/filter/Send/Stop/Reset route through public own widgets; no engine pointer/button state or native OS input is changed.',
            'Synthetic protocol-2 frames exercise draft/chat/transcript/ack presentation and outgoing normal Send/Stop payloads. No real coordinator, durable SQLite history, provider transport or live model advice is attested.',
            'Own handle render callbacks and bounds establish neither unobscured transcript visibility nor read receipts. No badge or target chips are implemented. Candidate startup automatically selects the existing fixture-configured assistant state directory; legacy geometry loads do not rewrite files. Released player configuration is unchanged.',
            'Supplied layout viewports exercise idle reflow, capture cancellation, undersized fallback and own-widget focus ownership without changing engine dimensions. No actual window resize/minimize acceptance.',
            'Composer object/text survives reflow; no physical keyboard focus/capture, cursor positioning, exact scroll anchor, font/accessibility or human readability claim. Header-only dragging and minimum 640x560 remain candidate policies.',
            'Abstract sRGB contrast and 0..127 normal-brightness channel conversion are detached policies; no native pixel/gamma/texture contrast, accessibility or all-control theme claim.',
            'Source/binary/compilation verification of public installed game APIs is distinct from official stable documented mod contracts.']}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['game-dir', 'jdk-home', 'java', 'save']:
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--candidate-dir', type=Path)
    p.add_argument('--validation', type=Path)
    args = p.parse_args()
    boundary = json.loads((ROOT / 'CHAT_INPUT_BOUNDARY_REVIEW.json').read_text())
    assert boundary['passed']
    assert sha(args.game_dir / 'SongsOfSyx.jar') == boundary['game_jar_sha256']
    assert sha(args.game_dir / 'info/SongsOfSyx-sources.jar') == boundary['source_archive_sha256']
    with zipfile.ZipFile(args.game_dir / 'info/SongsOfSyx-sources.jar') as archive:
        GAME_HASHES = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in GAME_PATHS}
    SOURCE_HASHES = {name: sha(ROOT / name) for name in SOURCES}
    candidate = ROOT / 'dev/candidates/chat-layout'
    with exclusive_fixture():
        run(args, scenario_override=candidate / 'StockpileScenario.java',
            extra_sources=[candidate / 'ChatPanel.java', candidate / 'ChatLayoutProbe.java',
                ROOT / 'dev/java/syx/assistant/candidate/GestureReducer.java',
                ROOT / 'dev/java/syx/assistant/candidate/PanelPreferences.java',
                ROOT / 'dev/java/syx/assistant/candidate/PanelTheme.java',
                ROOT / 'dev/java/syx/assistant/candidate/StatusLines.java'],
            candidate_chat_overlay=True, verifier=verify, report_name='native-chat-layout-validation.json',
            boundary_review_path=ROOT / 'CHAT_INPUT_BOUNDARY_REVIEW.json',
            completion_marker=('chat-layout-clean-exit.json', {'passed': True}))
