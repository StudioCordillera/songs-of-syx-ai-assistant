"""Pinned public cached-window getter review; never initializes game classes."""
import argparse
from datetime import datetime,timezone
import hashlib,json,re,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'dev'))
from verify_bytecode import disassemble,method,fingerprint
from review_ui_lifecycle_boundary import reader,require,compile_probe

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def review(game,jdk,catalog_path):
    jar=game/'SongsOfSyx.jar';archive=game/'info/SongsOfSyx-sources.jar';raw=catalog_path.read_bytes();catalog=json.loads(raw)
    if (catalog['game_jar_sha256'],catalog['source_archive_sha256'])!=(sha(jar),sha(archive)):raise ValueError('Catalog/game/source pair differs')
    required=['view.main.VIEW#s()','view.main.VIEW#b()','view.main.VIEW#world()',
        'view.sett.SettView#getWindow()','view.sett.invasion.SBattleView#getWindow()',
        'view.battle.BattleView#getWindow()','view.world.WorldView#window',
        'view.subview.GameWindow#tiles()','view.subview.GameWindow#pixels()',
        'view.subview.GameWindow#view()','view.subview.GameWindow#zoomout()',
        'view.subview.GameWindow#tile()','view.subview.GameWindow#consumeHover()']
    if not set(required)<={m['id'] for m in catalog['members']}:raise ValueError('Candidate declaration missing')
    java=['java','-Djava.home='+str(jdk.resolve())];records=[];cache={}
    def body(owner,signature):
        if owner not in cache:cache[owner]=disassemble(java,jar,owner)
        return method(cache[owner],signature)
    def stored(owner,signature,markers):
        b=body(owner,signature);reader(b,markers)
        if re.findall(r'// (?:InterfaceMethod|Method) ([^\s:]+):',b):raise ValueError('Stored reader gained unreviewed calls')
        records.append(dict(owner=owner,signature=signature,normalized_disassembly_sha256=fingerprint(b),no_direct_calls_heap_writes_allocations_backward_branches=True))
    for owner in ['view.sett.SettView','view.sett.invasion.SBattleView','view.battle.BattleView']:
        stored(owner,'public view.subview.GameWindow getWindow();',['window:','areturn'])
    for signature,marker in [('public snake2d.util.datatypes.RECTANGLE tiles();','tiles:'),
        ('public view.subview.GameWindow$PIXELWINDOW pixels();','pixels2:'),
        ('public snake2d.util.datatypes.RECTANGLE view();','viewWindow:'),('public int zoomout();','zoomout:'),
        ('public view.subview.GameWindow$SUB_MOUSE tile();','tile:')]:stored('view.subview.GameWindow',signature,[marker])
    for name,marker in [('x1','x:D'),('x2','width:D'),('y1','y:D'),('y2','height:D'),('width','width:D'),('height','height:D')]:
        stored('snake2d.util.datatypes.Rec','public int '+name+'();',[marker,'d2i'])
    for name,marker in [('x','X:D'),('y','Y:D')]:stored('snake2d.util.datatypes.Coo','public int '+name+'();',[marker])
    update=body('view.subview.GameWindow','public void update(float);')
    prefix=update[:update.index('13:')]
    require(prefix,['VIEW.UI:','UIView.manager:','IManager.open:','ifeq','12: return'])
    excluded=[]
    for signature,markers in [('public boolean consumeHover();',['hovered:','putfield']),
        ('public boolean hasZoomedOutMoreandConsumeThatMotherFZoom();',['hasZoomedOutMore:','putfield']),
        ('public void hover();',['MButt.clearWheelSpin:','MButt.consumeClick:'])]:
        b=body('view.subview.GameWindow',signature);require(b,markers)
        excluded.append(dict(signature=signature,normalized_disassembly_sha256=fingerprint(b),reason='State/input consuming method; never an observation'))
    hidden_setter=body('view.main.VIEW','public static void hide();');require(hidden_setter,['iconst_1','putfield','hideUI:'])
    excluded.append(dict(signature='view.main.VIEW.hide()',normalized_disassembly_sha256=fingerprint(hidden_setter),reason='Sets hidden UI true, not a toggle or unhide observer'))
    with zipfile.ZipFile(archive) as z:
        paths=['view/subview/GameWindow.java','view/world/WorldView.java','view/sett/SettView.java',
            'view/sett/invasion/SBattleView.java','view/battle/BattleView.java','snake2d/util/datatypes/Rec.java','snake2d/util/datatypes/Coo.java','view/main/VIEW.java']
        texts={p:z.read(p).decode() for p in paths};window=texts[paths[0]]
        require(window,['private boolean hovered;','private final SubMouse tile =','if (VIEW.UI().manager.open())',
            'int x = pixel.x() >> C.T_SCROLL;','int y = pixel.y() >> C.T_SCROLL;',
            '(int) (pixels.x1()/TILE_SIZE)','(int) (pixels.x2()/TILE_SIZE)','tiles.set(tX1, tX2, tY1, tY2);',
            'relative.set(VIEW.mouse().x() << zoomout, VIEW.mouse().y() << zoomout);'])
        require(texts['view/world/WorldView.java'],['public final GameWindow window = createwindow();','import static world.WORLD.PIXELS;'])
        for p in paths[2:5]:require(texts[p],['SETT.PIXEL_BOUNDS'])
        hashes={p:hashlib.sha256(z.read(p)).hexdigest() for p in paths}
    with tempfile.TemporaryDirectory(prefix='syx-viewport-access-') as tmp:
        probes=[compile_probe(java,jar,Path(tmp),'CachedViewportReaders',
            'int[] read() { view.subview.GameWindow[] ws={view.main.VIEW.s().getWindow(),view.main.VIEW.s().battle.getWindow(),view.main.VIEW.b().getWindow(),view.main.VIEW.world().window}; var w=ws[0]; var p=w.pixels(); var t=w.tiles(); var v=w.view(); return new int[]{w.zoomout(),p.x1(),p.y1(),p.x2(),p.y2(),t.x1(),t.y1(),t.x2(),t.y2(),v.x1(),v.y1(),v.x2(),v.y2(),w.tile().x(),w.tile().y()}; }'),
            compile_probe(java,jar,Path(tmp),'PrivateWindowHover',
                'boolean read() { return view.main.VIEW.s().getWindow().hovered; }','compiler.err.report.access')]
    return dict(passed=True,reviewed_at=datetime.now(timezone.utc).isoformat(),stage='Finite cached-viewport candidate review; no production mapping',
        game_jar_sha256=sha(jar),source_archive_sha256=sha(archive),catalog_sha256=hashlib.sha256(raw).hexdigest(),
        verifier_source_sha256=sha(Path(__file__)),helper_source_sha256={p:sha(ROOT/p) for p in ['dev/verify_bytecode.py','dev/review_ui_lifecycle_boundary.py']},
        public_declaration_members=required,selected_reader_checks=records,excluded_consuming_methods=excluded,
        update_management_early_return_disassembly_sha256=fingerprint(update),source_sha256=hashes,compile_probes=probes,
        game_methods_executed=0,inference_calls=0,conclusions=[
            'Public window routes compile for city, city tactical HUD, generated battle and campaign world; source binds city/battle windows to SETT pixel bounds and world window to WORLD pixels.',
            'Selected getters return stored references/primitive state. Rectangle accessors copy stored integer views; engine objects are mutable and must not escape a future update-thread DTO.',
            'pixels() exposes the rounded Pixels2 cache; tiles() exposes a separately cached rectangle using truncating pixel/tile conversion, not a conservative census of rendered/intersecting tiles. Screen view bounds do not prove occlusion, clipping or UI stacking.',
            'GameWindow.update returns before its ordinary cache refresh when management is open. Neither getter success nor hasMoved establishes freshness or validity of a user reference.',
            'tile() exposes cached sub-mouse coordinates. The hover flag is private; consumeHover clears state, hover consumes input, and the zoom-change consumer clears state. These are excluded from production reads. No selected/hovered tile, room or live cursor target is established.',
            'VIEW.hide sets the hidden flag true; repeated calls do not restore UI. No nonconsuming public unhide route is established by these inspected methods. Test hidden UI last rather than inject an input to reset it.',
            'A possible future observation is explicitly cached viewport geometry with view/scene/session and unavailable/freshness limits. No projection, native parity, scene matrix or all-menu acceptance follows from this static review.'
        ],limits=['Pinned shipped-source/binary/compiler evidence, not documented stable contracts, formal whole-game purity or exhaustive proof that no other public hover/selection route exists.',
            'Anonymous/internal types are inspected statically only; runtime probes compile external public API calls and never execute game methods.',
            'No reflection, screenshots, process memory, native input/OS automation, game initialization or proprietary body redistribution. Native public-action fixture evidence must be separate.'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--game-dir',type=Path,required=True);p.add_argument('--jdk-home',type=Path,required=True)
    p.add_argument('--catalog',type=Path,default=ROOT/'build/game-api-catalog.json');p.add_argument('--output',type=Path,default=ROOT/'VIEWPORT_BOUNDARY_REVIEW.json')
    a=p.parse_args();d=review(a.game_dir.resolve(),a.jdk_home.resolve(),a.catalog);a.output.write_text(json.dumps(d,indent=2)+'\n');print('Cached viewport boundary review passed.')
