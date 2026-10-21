"""Finite developer-only native own-surface/supplied-primitives gesture checks; no engine input injection."""
import argparse,json,hashlib,sys,zipfile
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from game_fixture_lock import exclusive_fixture
from run_stockpile_probe import run,sha
SOURCES=['dev/run_native_gesture_surface.py','dev/candidates/chat-gesture/StockpileScenario.java',
 'dev/candidates/chat-gesture/NativeGestureSurface.java','dev/java/syx/assistant/candidate/GestureReducer.java',
 'dev/run_stockpile_probe.py','dev/native_game_completion.py','mod/tests/LiveSmoke.java']
GAME_PATHS=['snake2d/Mouse.java','snake2d/MButt.java','snake2d/util/gui/clickable/CLICKABLE.java',
 'view/interrupter/InterGuisection.java','view/interrupter/Interrupter.java','view/interrupter/InterManager.java',
 'view/main/VIEW.java']
async def verify(state,manifest):
    for n,h in SOURCE_HASHES.items():assert sha(ROOT/n)==h,'Source changed during native run: '+n
    raw=json.loads((state/'stockpile-fixture.json').read_text());assert raw['passed']
    required={'short_launcher_toggle','immediate_header_drag','resize_rebuild','reject_wrong_surface_and_content','hidden_ui_cancel',
     'deactivation_cancel','scene_change_cancel','reset_layout','close_cancels_and_reopens_launcher','native_body_bounds','held_launcher_drag_clamps_without_opening','stationary_launcher_hold_suppresses_open'}
    assert set(raw['checks'])==required and len(raw['checks'])==len(required)
    assert raw['resized_panel_handle_callbacks']>=6 and raw['render_callbacks']>=6 and raw['post_rebuild_callbacks']>=3 and raw['own_section_generations']>=6
    return {'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),
      'scope':'Developer-only native own-widget adapter and supplied-primitives fixture. Not physical mouse/keyboard input, focus proof or chat/player acceptance.',
      'native_checks':raw,'source_sha256':SOURCE_HASHES,'selected_game_source_sha256':GAME_HASHES,
      'mod_jar_sha256':manifest['mod_jar_sha256'],'production_source_sha256':manifest['validation']['production_source_sha256'],
      'python_source_sha256':manifest['validation']['python_source_sha256'],'provider_calls':0,'native_input_injections':0,
      'production_integration':False,'explicit_fixture_save_requests':0,
      'public_adapter_boundary':[
        'Own ClickableAbs.clickA initiates capture only on the currently built launcher/header/resize handle; unrelated content/surface labels refuse.',
        'Own update copies CORE.getInput().getMouse().getCoo x/y and MButt.LEFT.isDown; no pointer setters or shared click counters.',
        'Own native geometry is bounded to public nativeWidth/nativeHeight; changed sizes rebuild own GuiSection, positions move own body.',
        'Own deactivation cancels; hidden UI/scene identity and reducer timeout/viewport guards cancel on sampling. No public focus guarantee is inferred.'],
      'limits':['One native resolution and disposable paused city; supplied gesture primitives, not physical routed clicks/held movement, OS input, out-of-window focus recovery or all scaling/scene acceptance.',
       'Fixture calls own begin/sample seam. The actual widget clickAction and update polling path compile and are source-inspected but no physical/native input is generated to drive them. A callback is not human-visible/unobscured display proof.',
       'At least six resized open-panel handle callbacks and three rebuilt launcher callbacks are counted. No pixels, clipping/accessibility/read receipts, real chat composer/transcript/citations, themes/persistence, typed attachments or unread badge are validated.',
       'Scene switch and UI hidden cancellation are driven through public test-only presentation actions in the copied profile. Return-to-menu/unload and reliable focus-loss detection remain separate gaps.',
       'Current production player JAR/helper/latest/previous ZIP remain unchanged; no new provider call, game action, game variable getter or shipped UI is implied.']}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['game-dir','jdk-home','java','save']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--candidate-dir',type=Path);p.add_argument('--validation',type=Path)
    a=p.parse_args();boundary=json.loads((ROOT/'CHAT_INPUT_BOUNDARY_REVIEW.json').read_text());assert boundary['passed']
    assert sha(a.game_dir/'SongsOfSyx.jar')==boundary['game_jar_sha256'] and sha(a.game_dir/'info/SongsOfSyx-sources.jar')==boundary['source_archive_sha256']
    with zipfile.ZipFile(a.game_dir/'info/SongsOfSyx-sources.jar') as z:GAME_HASHES={n:hashlib.sha256(z.read(n)).hexdigest() for n in GAME_PATHS}
    SOURCE_HASHES={n:sha(ROOT/n) for n in SOURCES}
    with exclusive_fixture():
        run(a,scenario_override=ROOT/'dev/candidates/chat-gesture/StockpileScenario.java',
          extra_sources=[ROOT/'dev/candidates/chat-gesture/NativeGestureSurface.java',ROOT/'dev/java/syx/assistant/candidate/GestureReducer.java'],
          verifier=verify,report_name='native-gesture-surface-validation.json',boundary_review_path=ROOT/'CHAT_INPUT_BOUNDARY_REVIEW.json',
          completion_marker=('gesture-surface-clean-exit.json',{'passed':True}))
