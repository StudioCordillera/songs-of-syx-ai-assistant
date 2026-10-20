"""Pin finite source-contract checks; never load game classes or publish bodies."""
import argparse
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parent.parent

def digest(path):return sha256(Path(path).read_bytes()).hexdigest()

def review(game):
    prior=json.loads((ROOT/'VIEWPORT_BOUNDARY_REVIEW.json').read_text())
    jar=game/'SongsOfSyx.jar';archive=game/'info/SongsOfSyx-sources.jar'
    if digest(jar)!=prior['game_jar_sha256'] or digest(archive)!=prior['source_archive_sha256']:
        raise ValueError('Game/source pair differs from stored-reader review')
    checks={
      'game/GAME.java':['game.onUpdateFinish.add(action);','game.updateI++;','for(ACTIONa:onUpdateFinish)a.exe();','if(speed==0){'],
      'snake2d/util/datatypes/RECTANGLE.java':['(x>=x1()&&x<x2())&&(y>=y1()&&y<y2())'],
      'view/sett/ui/subject/UISubjects.java':['Humanoida=subject.showing();'],
      'view/sett/ui/subject/UISubject.java':['if(VIEW.s().panels.added(panel))returna.a;returnnull;']}
    sources={}
    with zipfile.ZipFile(archive) as z:
        for name,markers in checks.items():
            raw=z.read(name);compact=re.sub(r'\s+','',raw.decode())
            if any(marker not in compact for marker in markers):
                raise ValueError('Finite source contract changed: '+name)
            sources[name]=sha256(raw).hexdigest()
    own=(ROOT/'mod/src/main/java/syx/assistant/UiContextCollector.java').read_text()
    if 'Arrays.asList(r.x1(),r.y1(),r.x2(),r.y2())' not in own:
        raise ValueError('Primitive rectangle detachment changed')
    if re.search(r'window\.(?:update|hover|consume\w*|set\w*)\s*\(',own):
        raise ValueError('Camera observation gained a known mutating/consuming call')
    mcp=(ROOT/'syx_mcp.py').read_text()
    if '"scene": s.scene' not in mcp or "return {'state':status,'context':snapshot.ui_context" not in mcp:
        raise ValueError('MCP scene/context binding changed')
    return dict(passed=True,reviewed_at=datetime.now(timezone.utc).isoformat(),
        stage='Finite cached viewport/rectangle/subject-panel/envelope contract review; no new official stable contract',
        game_jar_sha256=digest(jar),source_archive_sha256=digest(archive),
        stored_reader_review_sha256=digest(ROOT/'VIEWPORT_BOUNDARY_REVIEW.json'),
        source_sha256=sources,verifier_source_sha256=digest(Path(__file__)),
        own_source_sha256={n:digest(ROOT/n) for n in ['mod/src/main/java/syx/assistant/UiContextCollector.java','syx_mcp.py','mod/tests/ViewportScenario.java']},
        conclusions=[
          'Paused GAME update advances updateI before ordered after-update actions. The production callback is registered before the fixture; bounded getter samples are taken before fixture phase mutations and matched to exported tick. This does not assert tick uniqueness during arbitrary unpaused/faulted engine execution.',
          'RECTANGLE point membership uses exclusive x2/y2; named deployment-bound objects and explicit camera vectors need not share a JSON shape. This is not a renderer/edge-intersection census.',
          'UISubjects.current delegates to showing(), which checks live subject-panel membership. An alleged missing panel guard is not a demonstrated defect. Underlying membership still does not prove unobscured display.',
          'MCP UI context includes the same snapshot status/scene. City versus battlefield is carried by state.scene.settlement_scene_kind; geometry alone is not a durable map identity or authority to reuse bounds in a later scene.',
          'The mapping copies rectangle primitives and invokes none of the named camera refresh/hover/set/consume routes. Complete transitive purity and exhaustive API absence are not established by string markers.'],
        game_methods_executed=0,inference_calls=0)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game-dir',type=Path,required=True)
    p.add_argument('--output',type=Path,default=ROOT/'CACHED_VIEWPORT_CONTRACT_REVIEW.json')
    a=p.parse_args();a.output.write_text(json.dumps(review(a.game_dir.resolve()),indent=2)+'\n')
    print('Cached viewport source contracts matched')
