"""Fixed public warehouse furniture catalog probe for an original teaching schematic; no layout placement."""
import argparse,json,hashlib,sys,zipfile
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from game_fixture_lock import exclusive_fixture
from run_stockpile_probe import run,sha
SOURCES=['dev/run_blueprint_catalog.py','dev/candidates/blueprint-example/StockpileScenario.java',
 'dev/run_stockpile_probe.py','dev/native_game_completion.py','mod/tests/LiveSmoke.java']
GAME_PATHS=['settlement/room/infra/stockpile/ROOM_STOCKPILE.java','settlement/room/infra/stockpile/Constructor.java',
 'settlement/room/main/furnisher/Furnisher.java','settlement/room/main/furnisher/FurnisherItemGroup.java',
 'settlement/room/main/furnisher/FurnisherItem.java','settlement/room/main/furnisher/FurnisherItemTile.java']
async def verify(state,manifest):
    for n,h in SOURCE_HASHES.items():assert sha(ROOT/n)==h,n
    raw=json.loads((state/'stockpile-fixture.json').read_text());assert raw['passed']
    assert raw['width']==2 and raw['height']==1 and raw['rotation']==0 and raw['size']==0 and raw['must_be_indoors'] is True
    assert [(t['x'],t['y'],t['blocker'],t['must_be_reachable']) for t in raw['cells']]==[(0,0,True,True),(1,0,True,False)]
    assert len({t['tile_index'] for t in raw['cells']})==2
    return {'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),
      'scope':'Fixed public native catalog item footprint/access flags for an original teaching schematic. No room construction, resource capacity, world placement/pathing, optimality or execution acceptance.',
      'game_version':'0.71.44','catalog_item':raw,'source_sha256':SOURCE_HASHES,'selected_game_source_sha256':GAME_HASHES,
      'source_qualification':'Installed public source/binary and external compiler/native verification, not separately documented stable furnishing contracts.',
      'mod_jar_sha256':manifest['mod_jar_sha256'],'production_source_sha256':manifest['validation']['production_source_sha256'],
      'python_source_sha256':manifest['validation']['python_source_sha256'],'provider_calls':0,'explicit_fixture_save_requests':0,
      'public_read_routes':['SETT.ROOMS().STOCKPILE.constructor','Furnisher.pgroups/mustBeIndoors','FurnisherItemGroup.index/size/rotations/item',
       'FurnisherItem.index/width/height/get/rotation','FurnisherItemTile.index/isBlocker/mustBeReachable'],
      'excluded_routes':['Room create/build/placement/embryo setup','Furniture/item placement probes and game pathfinders','Game resource/stat/capacity formulas','Private fields/reflection, process memory, screenshot or input automation'],
      'limits':['One current installed catalog item in one paused disposable copied city, not arbitrary mods/versions/furniture or actual placement validation.',
       'Occupied footprint and public must-be-reachable flags do not prove a future room/building is legal, an entrance is usable in the actual map, or storage/performance/cost optimality.',
       'No proprietary source, sprite, save layout, community blueprint/image/video or third-party code is redistributed; only selected factual public metadata and our conclusions.',
       'The production MCP/client/downloads remain unchanged. An authored illustrative grid is not an executable plan or tool authorization.']}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['game-dir','jdk-home','java','save']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--candidate-dir',type=Path);p.add_argument('--validation',type=Path)
    a=p.parse_args();boundary=json.loads((ROOT/'STOCKPILE_BOUNDARY_REVIEW.json').read_text());assert boundary['passed']
    assert sha(a.game_dir/'SongsOfSyx.jar')==boundary['game_jar_sha256'] and sha(a.game_dir/'info/SongsOfSyx-sources.jar')==boundary['source_archive_sha256']
    with zipfile.ZipFile(a.game_dir/'info/SongsOfSyx-sources.jar') as z:GAME_HASHES={n:hashlib.sha256(z.read(n)).hexdigest() for n in GAME_PATHS}
    SOURCE_HASHES={n:sha(ROOT/n) for n in SOURCES}
    with exclusive_fixture():
        run(a,scenario_override=ROOT/'dev/candidates/blueprint-example/StockpileScenario.java',verifier=verify,
          report_name='blueprint-catalog-validation.json',completion_marker=('blueprint-catalog-clean-exit.json',{'passed':True}))
