"""Static licensed-source/compiler review for a future mod-owned draggable chat.

No game initialization, native input, screenshots, production edits or inference.
Publishes only our conclusions, anchors/hashes and finite compiler checks.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'dev'))
from review_ui_lifecycle_boundary import compile_probe,reader
from verify_bytecode import disassemble,method,fingerprint


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def review(game,jdk):
    jar=game/'SongsOfSyx.jar';archive=game/'info/SongsOfSyx-sources.jar'
    audit=json.loads((ROOT/'api-audit.json').read_text())
    if sha(jar)!=audit['game_jar_sha256'] or sha(archive)!=audit['source_archive_sha256']:
        raise ValueError('Game/source differs from current audit')
    java=['java','-Djava.home='+str(jdk.resolve())]
    routes=[('snake2d.CORE','public static snake2d.Input getInput();',['getstatic','input:']),
        ('snake2d.Input','public snake2d.Mouse getMouse();',['getfield','mouse:']),
        ('snake2d.Mouse','public snake2d.util.datatypes.Coo getCoo();',['getfield','MOUSE_COO:']),
        ('snake2d.MButt','public boolean isDown();',['getfield','isDown:'])]
    records=[]
    with zipfile.ZipFile(archive) as z:
        for owner,signature,markers in routes:
            body=method(disassemble(java,jar,owner),signature);reader(body,markers)
            path=owner.replace('.','/')+'.java'
            records.append(dict(owner=owner,signature=signature,source_path=path,
                source_sha256=hashlib.sha256(z.read(path)).hexdigest(),
                normalized_disassembly_sha256=fingerprint(body),direct_reader_check=True))
        source_records=[]
        for path,markers,conclusion in [
            ('snake2d/Mouse.java',['if (!CORE.getGraphics().isFocused())','return MOUSE_COO;','newX >= 0','newY >= 0'],
             'Pointer getter returns an engine-owned mutable Coo. Engine polling can retain previous coordinates while unfocused or outside bounds. Copy primitives on the game thread; never mutate or treat them as guaranteed current/focused/hovered-target identity.'),
            ('snake2d/MButt.java',['public boolean isDown()','return isDown;','public boolean consumeClick()'],
             'isDown reads held-button state without consuming clicks. It is not a release callback or mod ownership claim. Click consumption remains framework-owned; never mutate global click counters.'),
            ('view/interrupter/InterGuisection.java',['section.hover(mCoo)','section.click();','section.render(r, ds);'],
             'Own section routes public framework hover/click/render. Existing native fixtures consume only own controls. A future hold/drag state machine must retain own capture and isolate composer/buttons.'),
            ('view/interrupter/InterManager.java',['for (Interrupter i : inters)','if (!i.render(r, ds))'],
             'A render callback does not alone establish unobscured human visibility: manager layers may draw other interrupters. Unread acknowledgements need a separately reviewed visibility rule.')]:
            raw=z.read(path);text=raw.decode()
            for marker in markers:
                if marker not in text:raise ValueError('Reviewed input source changed: '+path)
            source_records.append(dict(path=path,source_sha256=hashlib.sha256(raw).hexdigest(),
                anchor_lines=[text[:text.index(marker)].count('\n')+1 for marker in markers],conclusion=conclusion))
    with tempfile.TemporaryDirectory(prefix='chat-input-',dir=ROOT/'runtime') as temporary:
        directory=Path(temporary)
        probes=[compile_probe(java,jar,directory,'ChatPointerRead',
            'int[] read(){ snake2d.util.datatypes.Coo p=snake2d.CORE.getInput().getMouse().getCoo(); return new int[]{p.x(),p.y()}; }'),
            compile_probe(java,jar,directory,'ChatHeldRead','boolean read(){ return snake2d.MButt.LEFT.isDown(); }'),
            compile_probe(java,jar,directory,'ChatBoundsRead','int[] read(){ return new int[]{snake2d.CORE.getGraphics().nativeWidth,snake2d.CORE.getGraphics().nativeHeight}; }'),
            compile_probe(java,jar,directory,'ChatFocusExcluded','boolean read(){ return snake2d.CORE.getGraphics().isFocused(); }',
                diagnostic='compiler.err.not.def.public.cant.access')]
    return dict(passed=True,reviewed_at=datetime.now(timezone.utc).isoformat(),
        stage='Static candidate input/visibility boundary only; no production drag/resize/badge',
        game_jar_sha256=sha(jar),source_archive_sha256=sha(archive),direct_readers=records,
        selected_source_reviews=source_records,compiler_probes=probes,
        reviewer_source_sha256=sha(Path(__file__)),game_initializations=0,inference_calls=0,
        exclusions=['No pointer setter, private focus access, click consumption, global counter mutation or OS/native input injection.',
            'Do not retain mutable engine coordinate handles, infer selected game objects from pointer coordinates or acknowledge unread solely because render ran.'],
        limits=['Finite selected source/binary/compiler review, not an exhaustive public API inventory or documented stable SCRIPT contract.',
            'No actual hold/release/focus-loss/drag/resize/occlusion/scaling acceptance; these remain explicit native candidate gates.'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game-dir',type=Path,required=True);p.add_argument('--jdk-home',type=Path,required=True)
    p.add_argument('--output',type=Path,default=ROOT/'CHAT_INPUT_BOUNDARY_REVIEW.json');a=p.parse_args()
    result=review(a.game_dir,a.jdk_home);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print('Static chat input boundary review passed:',a.output)
