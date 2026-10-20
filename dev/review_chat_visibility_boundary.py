"""Static selected render-pipeline review; no game initialization or pixel capture."""
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
from review_ui_lifecycle_boundary import compile_probe,reader,require
from verify_bytecode import disassemble,method,fingerprint


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def review(game,jdk):
    jar=game/'SongsOfSyx.jar';archive=game/'info/SongsOfSyx-sources.jar';audit=json.loads((ROOT/'api-audit.json').read_text())
    if sha(jar)!=audit['game_jar_sha256'] or sha(archive)!=audit['source_archive_sha256']:raise ValueError('Game/source differs from pinned audit')
    java=['java','-Djava.home='+str(jdk.resolve())];records=[]
    with zipfile.ZipFile(archive) as z:
        for owner,signature,markers,direct in [
            ('view.main.IMouseMessage','public util.gui.misc.GBox get();',['timer:','timed:','normal:'],True),
            ('util.gui.misc.GBox','public boolean emptyIs();',['getfield'],True),
            ('view.main.VIEW','public static boolean hideUI();',['hideUI:'],True),
            ('view.interrupter.Interrupter','public final boolean isActivated();',['addManager:'],True),
            ('view.main.IMouseMessage','public void render(snake2d.Renderer, float);',['GBox.render:','GBox.clear:'],False),
            ('view.main.VIEW','protected void render(snake2d.Renderer, float);',['IMouseMessage.render:','InterManager.render:'],False),
            ('view.interrupter.InterManager','public boolean render(snake2d.Renderer, float);',['Interrupter.render:','Renderer.newLayer:'],False)]:
            body=method(disassemble(java,jar,owner),signature);(reader if direct else require)(body,markers)
            path=owner.replace('.','/')+'.java'
            records.append(dict(owner=owner,signature=signature,source_path=path,source_sha256=hashlib.sha256(z.read(path)).hexdigest(),normalized_disassembly_sha256=fingerprint(body),direct_reader_check=direct,engine_pipeline_review_only=not direct))
        source=[]
        for path,markers,note in [
            ('view/main/IMouseMessage.java',['normal.clear();','public GBox get()','boolean isOn()'],
             'The normal tooltip buffer is cleared by rendering; public get returns mutable timer-selected buffer. A post-render empty buffer cannot establish that no tooltip was drawn. isOn is not externally public.'),
            ('view/main/VIEW.java',['if (hideUI)','inters.mouseMessage.render(r, ds);','GAME.script().callback.render(r, ds);','inters.manager.render(r, ds)'],
             'Selected root skips UI when hidden, otherwise tooltip/script render stages precede the global manager. Manager callbacks alone do not describe earlier layers or other scripts.'),
            ('view/interrupter/InterManager.java',['for (Interrupter i : inters)','if (!i.render(r, ds))','private final Collection inters'],
             'Multiple active interrupters can render in successive layers. The inspected collection is private; this is not a complete global occlusion reader or an exhaustive absence-of-API proof.')]:
            raw=z.read(path);text=raw.decode()
            for marker in markers:
                if marker not in text:raise ValueError('Selected visibility source changed')
            source.append(dict(path=path,source_sha256=hashlib.sha256(raw).hexdigest(),anchor_lines=[text[:text.index(m)].count('\n')+1 for m in markers],conclusion=note))
    with tempfile.TemporaryDirectory(prefix='chat-visibility-static-',dir=ROOT/'runtime') as temporary:
        directory=Path(temporary)
        probes=[compile_probe(java,jar,directory,'ChatTooltipRead','boolean read(){return view.main.VIEW.inters().mouseMessage.get().emptyIs();}'),
            compile_probe(java,jar,directory,'ChatKnownHiddenRead','boolean read(){return view.main.VIEW.hideUI();}'),
            compile_probe(java,jar,directory,'ChatOwnRenderHooks','static final class Own extends view.interrupter.InterGuisection { Own(){super(null);} @Override protected void otherAdd(view.interrupter.Interrupter i){} @Override protected void afterTick(){} @Override protected boolean render(snake2d.Renderer r,float ds){return true;} }'),
            compile_probe(java,jar,directory,'ChatPrivateTooltipExcluded','boolean read(){return view.main.VIEW.inters().mouseMessage.isOn();}',diagnostic='compiler.err.not.def.public.cant.access')]
    return dict(passed=True,reviewed_at=datetime.now(timezone.utc).isoformat(),game_jar_sha256=sha(jar),source_archive_sha256=sha(archive),
        stage='Selected public/engine source boundary only; no production visibility reader or badge',methods=records,selected_source_reviews=source,compiler_probes=probes,
        reviewer_source_sha256=sha(Path(__file__)),game_initializations=0,inference_calls=0,
        limits=['Source/binary/compiler verification, not a stable documented SCRIPT contract or complete global UI inventory.',
            'Engine pipeline methods are inspected, not promoted to observer calls. Production live game data remains update-thread only.',
            'No private tooltip/manager/focus fallback. Actual native callback probe is separate finite evidence.',
            'Receipt transport/segment coverage cannot establish actual unobscured display until a reviewed native gate or explicit player acknowledgement policy is supplied.'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game-dir',type=Path,required=True);p.add_argument('--jdk-home',type=Path,required=True)
    p.add_argument('--output',type=Path,default=ROOT/'CHAT_VISIBILITY_BOUNDARY_REVIEW.json');a=p.parse_args()
    result=review(a.game_dir,a.jdk_home);a.output.write_text(json.dumps(result,indent=2)+'\n');print('Selected visibility source review passed:',a.output)
