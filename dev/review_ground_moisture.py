"""Review finite public stored-moisture readers in licensed source/binary; no game initialization."""
import argparse
from datetime import datetime,timezone
import hashlib,json,re,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'dev'))
from verify_bytecode import disassemble,method,fingerprint
from review_ui_lifecycle_boundary import reader,require,compile_probe

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def review(game,jdk,catalog_path):
    jar=game/'SongsOfSyx.jar';archive=game/'info/SongsOfSyx-sources.jar'
    raw=catalog_path.read_bytes();catalog=json.loads(raw)
    if (catalog['game_jar_sha256'],catalog['source_archive_sha256'])!=(sha(jar),sha(archive)):
        raise ValueError('Declaration catalog differs from licensed game/source pair')
    required=['settlement.main.SETT#GROUND()','settlement.main.SETT#IN_BOUNDS(int,int)',
        'settlement.main.SETT#TWIDTH','settlement.tilemap.ground.Ground#MOISTURE_BASE',
        'settlement.tilemap.ground.Ground#MOISTURE_CURRENT','snake2d.util.map.MAP_DOUBLE#get(int,int)',
        'snake2d.util.map.MAP_DOUBLE#get(int)','snake2d.util.sets.Bitsmap1D#get(int)']
    if not set(required)<={m['id'] for m in catalog['members']}:raise ValueError('Candidate declaration missing')
    java=['java','-Djava.home='+str(jdk.resolve())];records=[]
    def inspect(owner,signature,markers,calls):
        body=method(disassemble(java,jar,owner),signature);reader(body,markers)
        found=re.findall(r'// (?:InterfaceMethod|Method) ([^\s:]+):',body)
        if found!=calls:raise ValueError('Candidate call chain changed: '+owner+' '+signature)
        records.append(dict(owner=owner,signature=signature,normalized_disassembly_sha256=fingerprint(body),
            no_direct_heap_write_allocation_backward_branch=True,direct_calls=found))
    for owner,field in [('settlement.tilemap.ground.Ground$2','mapMoistureBase'),('settlement.tilemap.ground.Ground$3','mapMoistureCurrent')]:
        inspect(owner,'public double get(int, int);',['SETT.IN_BOUNDS:','SETT.TWIDTH:','get:(I)D'],['settlement/main/SETT.IN_BOUNDS','get'])
        inspect(owner,'public double get(int);',[field+':','Bitsmap1D.get:','double 0.06666666666666667d','dmul'],['snake2d/util/sets/Bitsmap1D.get'])
    inspect('snake2d.util.sets.Bitsmap1D','public int get(int);',['outof:I','bits:[J','laload','land'],[])
    inspect('settlement.main.SETT','public static boolean IN_BOUNDS(int, int);',['TILE_BOUNDS:','RECTANGLE.holdsPoint:'],['snake2d/util/datatypes/RECTANGLE.holdsPoint'])
    inspect('snake2d.util.datatypes.RECTANGLE','public default boolean holdsPoint(double, double);',['x1:','x2:','y1:','y2:'],['x1','x2','y1','y2'])
    for name,marker in [('x1','x:D'),('x2','width:D'),('y1','y:D'),('y2','height:D')]:
        inspect('snake2d.util.datatypes.Rec','public int '+name+'();',[marker],[])
    inspect('settlement.main.SETT','public static settlement.tilemap.ground.Ground GROUND();',['TileMap.ground:'],[])
    with zipfile.ZipFile(archive) as z:
        paths=['settlement/tilemap/ground/Ground.java','snake2d/util/sets/Bitsmap1D.java',
            'settlement/main/SETT.java','snake2d/util/datatypes/RECTANGLE.java','snake2d/util/datatypes/Rec.java','settlement/environment/SettEnvMap.java','settlement/weather/WeatherMoisture.java']
        sources={p:z.read(p).decode() for p in paths};ground=sources[paths[0]]
        require(ground,['public static final int MOISTURE_MAX = 15;','public static final double MOISTURE_MAXI = 1.0/MOISTURE_MAX;',
            'mapMoistureBase = new Bitsmap1D(0, 4, SETT.TAREA);','mapMoistureCurrent = new Bitsmap1D(0, 4, SETT.TAREA);',
            'return mapMoistureBase.get(tile)*MOISTURE_MAXI;','return mapMoistureCurrent.get(tile)*MOISTURE_MAXI;',
            'mapMoistureBase.get(tile) + SETT.ENV().map.WATER_SWEET.get(tile)*MOISTURE_MAX',
            'return MOISTURE_BASE.get(tile) + SETT.ENV().map.WATER_SWEET.get(tile)*2;',
            'if (f < n)', 'f++;','f--;','mapMoistureCurrent.set(tile, f);'])
        require(sources['settlement/weather/WeatherMoisture.java'],['return CLAMP.d(getD()*4.0, 0, 1);'])
        source_hashes={p:hashlib.sha256(z.read(p)).hexdigest() for p in paths}
    with tempfile.TemporaryDirectory(prefix='syx-ground-access-') as tmp:
        probe=compile_probe(java,jar,Path(tmp),'StoredGroundMoisture',
            'double[] read(int x,int y) { var g=settlement.main.SETT.GROUND(); snake2d.util.map.MAP_DOUBLE b=g.MOISTURE_BASE,c=g.MOISTURE_CURRENT; return new double[]{b.get(x,y),c.get(x,y),b.get(x+y*settlement.main.SETT.TWIDTH),c.get(x+y*settlement.main.SETT.TWIDTH)}; }')
    return dict(passed=True,reviewed_at=datetime.now(timezone.utc).isoformat(),stage='Candidate stored tile moisture, not production mapping',
        game_jar_sha256=sha(jar),source_archive_sha256=sha(archive),catalog_sha256=hashlib.sha256(raw).hexdigest(),
        verifier_source_sha256=sha(Path(__file__)),helper_source_sha256={n:sha(ROOT/n) for n in ['dev/verify_bytecode.py','dev/review_ui_lifecycle_boundary.py']},
        public_declaration_members=required,selected_method_checks=records,additional_source_sha256=source_hashes,compile_probe=probe,
        game_methods_executed=0,inference_calls=0,conclusions=[
            'Base/current are separate stored four-bit tile maps normalized by 1/15. In-bounds values are quantized 0..1, not exact unquantized water content.',
            'Coordinate wrappers check bounds and return zero outside them. A future observer must reject out-of-map coordinates; getter zero alone cannot prove valid dry terrain.',
            'Current stored map approaches a clamped base-plus-water target one raw step per adjust call. It is not the same as MOISTURE_TOT; exact age/convergence/update cadence is unknown.',
            'MOISTURE_TOT computes base + 2*WATER_SWEET without final clamping and calls an environmental reader. It is excluded from this stored-reader review and native candidate route.',
            'Weather precipitation/growth and moisture overlays are separate concepts. These tile readers do not establish soil fertility, crop/pasture yield, irrigation eligibility, construction suitability or forecasts.',
            'Selected read-only bytecode chain has no direct heap write/allocation/backward branch; no setter, adjust, initialization, rendering or update is invoked by the candidate observation.'
        ],limits=[
            'Shipped source/binary/compiler review, not separately documented stable public mod contracts or whole-game formal purity/thread-safety proof.',
            'Runtime scene/coordinate/parity/cost evidence is separate. No new production field, MCP capability, all-state coverage or latest-player test claim.',
            'Anonymous implementation names are inspected statically only; candidate runtime code calls public MAP_DOUBLE.get, never names those classes or accesses private/package fields.',
            'Metadata/hashes only; no proprietary source/bodies redistributed. No reflection, screenshots, process memory or native input.'
        ])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game-dir',type=Path,required=True);p.add_argument('--jdk-home',type=Path,required=True)
    p.add_argument('--catalog',type=Path,default=ROOT/'build/game-api-catalog.json');p.add_argument('--output',type=Path,default=ROOT/'GROUND_MOISTURE_BOUNDARY_REVIEW.json')
    a=p.parse_args();r=review(a.game_dir.resolve(),a.jdk_home.resolve(),a.catalog);a.output.write_text(json.dumps(r,indent=2)+'\n');print('Stored ground-moisture boundary review passed.')
