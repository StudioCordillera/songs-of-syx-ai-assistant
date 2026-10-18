"""Review regional stored output candidates without loading licensed game classes.

Reports metadata/hashes/semantics, never game source bodies or observed values.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'dev'))
from verify_bytecode import disassemble,method,fingerprint
from review_stockpile_boundary import stored_reader


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def require(body,markers):
    for marker in markers:
        if marker not in body:raise ValueError('Regional output semantics changed: '+marker)


def check_pair(game,catalog_path):
    raw=catalog_path.read_bytes()
    if len(raw)>32*1024*1024:raise ValueError('Declaration catalog exceeds 32 MiB')
    catalog=json.loads(raw)
    if any(catalog[k]!=sha(game/p) for k,p in [('game_jar_sha256','SongsOfSyx.jar'),('source_archive_sha256','info/SongsOfSyx-sources.jar')]):
        raise ValueError('Catalog differs from licensed game/source pair')
    return catalog,hashlib.sha256(raw).hexdigest()


def review(game,jdk,catalog_path):
    catalog,catalog_hash=check_pair(game,catalog_path);jar=game/'SongsOfSyx.jar';archive=game/'info/SongsOfSyx-sources.jar'
    required=['world.region.RD#OUTPUT()','world.region.RDOutputs#get(init.trade.TRADABLE)',
        'world.region.RDOutputs.RDOutput#yearlyAccumilation','init.trade.TR#get(init.resources.RESOURCE)',
        'init.trade.TRADABLE#index()','init.trade.TRADABLE#key()',
        'world.region.RDOutputs.RDResource#daysUntilDailydelivery()',
        'util.data.DataO.DataAbs#get(T)']
    if not set(required)<={m['id'] for m in catalog['members']}:raise ValueError('Candidate public declaration missing')
    java=['java','-Djava.home='+str(jdk.resolve())];cache={};checks=[];sources={}
    with zipfile.ZipFile(archive) as z:
        def inspect(owner,signature,markers,stored=False,path=None):
            if owner not in cache:cache[owner]=disassemble(java,jar,owner)
            body=method(cache[owner],signature)
            (stored_reader if stored else require)(body,markers)
            path=path or owner.split('$')[0].replace('.','/')+'.java'
            sources[path]=sha_bytes(z.read(path))
            checks.append({'owner':owner,'signature':signature,'source_path':path,'source_sha256':sources[path],
                'normalized_disassembly_sha256':fingerprint(body),'direct_stored_reader_check':stored})
            return body
        inspect('world.region.RD','public static world.region.RDOutputs OUTPUT();',['self:','resources:'],True)
        inspect('init.trade.TR','public static init.trade.TRADABLEO<init.resources.RESOURCE> get(init.resources.RESOURCE);',['RESOURCE.index:','ArrayListGrower.get:'],True)
        inspect('world.region.RDOutputs','public world.region.RDOutputs$RDResource get(init.trade.TRADABLE);',['TRADABLE.index:','LIST.get:'],True)
        inspect('util.data.DataO$DataAbs','public int get(T);',['.data:','laload','lushr','land','l2i'],True)
        inspect('world.region.RD$RDInit$1','protected long[] data(world.map.regions.Region);',['Region.index:','aaload'],True,path='world/region/RD.java')
        inspect('world.region.RDOutputs$RDResource','public int daysUntilDailydelivery();',['seasonalOffset:','MATH.ETA:'],True)
        inspect('world.region.RDOutputs$RDOutput','public int daysUntilDailydelivery();',['MATH.ETA:'],True)
        inspect('snake2d.util.MATH','public static int ETA(int, int, int);',['isub','iadd'],True)
        count=inspect('world.region.updating.Shipper','private void count(world.region.RDOutputs$RDResource, world.map.regions.Region, double);',
            ['boostYearlyPart:','TIME.secondsPerDayI:','RND.rFloat:','yearlyAccumilation:','INT_O$INT_OE.inc:'])
        clear=inspect('world.region.updating.Shipper','private void clear(world.region.RDOutputs$RDResource, world.map.regions.Region);',
            ['daysUntilDailydelivery:','ifne','yearlyAccumilation:','INT_O$INT_OE.set:'])
        amount=inspect('world.region.updating.Shipper','private int amount(world.region.RDOutputs$RDResource, world.map.regions.Region, double);',
            ['Boostable.get:','Math.ceil:','daysUntilDailydelivery:','yearlyAccumilation:','iadd'])
        ship=inspect('world.region.updating.Shipper','public void ship(world.map.regions.Region, double);',
            ['Region.faction:','Region.besieged:','capitolRegion:','Region.capitol:','count:','amount:',
             'caravans:','Shipment.loadAndReserve:','clear:'])
        if ship.index('Shipment.loadAndReserve:')>=ship.index('clear:'):raise ValueError('Clear no longer follows loading/reservation')
        inspect('world.region.RDOutputs$1','public void change(world.map.regions.Region, game.faction.Faction, game.faction.Faction);',
            ['RDOutputs.ALL:','yearlyAccumilation:','INT_O$INT_OE.set:'],path='world/region/RDOutputs.java')
        cache_body=inspect('world.region.RDBoostCache','public double get(world.map.regions.Region);',
            ['INT_O$INT_OE.set:','pget:'])
        try:stored_reader(cache_body)
        except ValueError:pass
        else:
            # Interface setter invocation is a transitive write even without putfield.
            if 'INT_O$INT_OE.set:' not in cache_body:raise ValueError('Cache mutation exclusion changed')
        for path,markers in {
            'world/region/RDOutputs.java':['yearlyAccumilation = init.count.new DataInt(', 'r.yearlyAccumilation.set(reg, 0)'],
            'world/region/RD.java':['protected long[] data(Region t)', 'return regionData[t.index()]'],
            'world/region/updating/RDUpdater.java':['private float[] timers','shipper.ship(r, ship)','shipper.ship(r, build)'],
            'util/data/DataO.java':['public int get(T t)', '((data(t)[iLong] >>> scroll) & mask)'],
        }.items():
            raw=z.read(path);require(raw.decode(),markers);sources[path]=sha_bytes(raw)
    with tempfile.TemporaryDirectory(prefix='syx-regional-output-') as tmp:
        source=Path(tmp)/'RegionalOutputProbe.java'
        source.write_text('final class RegionalOutputProbe { int read(world.map.regions.Region region, init.resources.RESOURCE resource) { var tradable=init.trade.TR.get(resource); var output=world.region.RD.OUTPUT().get(tradable); return output.yearlyAccumilation.get(region); } }\n')
        result=subprocess.run([*java,'-m','jdk.compiler/com.sun.tools.javac.Main','-proc:none','--release','16',
            '-cp',str(jar),'-d',tmp,str(source)],capture_output=True,text=True,timeout=30)
        if result.returncode:raise ValueError('Regional public stored-reader route no longer compiles')
        probe_hash=sha(source)
    return {'passed':True,'reviewed_at':datetime.now(timezone.utc).isoformat(),
        'stage':'Static candidate only; production regional-output mapping is not implemented by this review',
        'game_jar_sha256':sha(jar),'source_archive_sha256':sha(archive),'catalog_sha256':catalog_hash,
        'candidate_public_members':required,'method_checks':checks,'additional_source_sha256':sources,
        'compile_probe':{'passed':True,'source_sha256':probe_hash,'annotation_processing':False,'game_classes_executed':False},
        'reviewer_source_sha256':{n:sha(ROOT/n) for n in ['dev/review_regional_output_boundary.py','dev/review_stockpile_boundary.py','dev/verify_bytecode.py']},
        'conclusions':[
            'Resource -> TR.get(resource) -> RD.OUTPUT().get(tradable) -> yearlyAccumilation.get(region) compiles using ordinary public members. The reviewed DataAbs getter decodes packed region storage; its data provider indexes the stored region array. No direct write/allocation/backward branch is present in these selected reader bodies. This is not a full transitive purity proof.',
            'The stored integer is an accrued scheduled-output counter, not current inventory, an annual delivered total, full regional production or an arrival forecast. Shipper count adds the yearly-part boost scaled by elapsed game days with stochastic fractional rounding. The exact last-update time is private.',
            'The accumulator contributes to amount only on its configured delivery day. After a positive amount is loaded/reserved into a successfully created shipment, clear resets the accumulator only on that configured day. Unowned, besieged, no-capital and player-capital cases can skip shipping; missing shipments do not establish delivery.',
            'The owner-change callback resets output accumulators. This is static reset-path evidence, not a native ownership-transfer or rollover test.',
            'daysUntilDailydelivery computes a cyclic configured day offset, with a growable seasonal offset when present. It is not an ETA, reachability guarantee, active shipping condition or actual arrival time.',
            'RDBoostCache.get can invoke a setter and refresh computed state. Broad boost/production calculations and mutable building previews remain excluded from a stored-observation candidate. Native probe must not call shipper, delivery, squeeze, boost or cache refresh methods.'
        ],'limits':['Shipped-source/binary verification, not a separately documented stable official mod contract.',
            'Only named routes are reviewed. Public metadata does not prove runtime reachability, cost, all scenes or all resource/non-resource tradables.',
            'No production exposure, native counter parity, natural nonzero/seasonal rollover, cap/fault or full collector cost proof is supplied by this static report.',
            'Licensed source/bytecode bodies are not published. No reflection, process memory, screenshot, native input or game method execution.']}


def sha_bytes(raw):return hashlib.sha256(raw).hexdigest()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--game-dir',type=Path,required=True);p.add_argument('--jdk-home',type=Path,required=True)
    p.add_argument('--catalog',type=Path,default=ROOT/'build/game-api-catalog.json')
    p.add_argument('--output',type=Path,default=ROOT/'REGIONAL_OUTPUT_BOUNDARY_REVIEW.json')
    a=p.parse_args();r=review(a.game_dir.resolve(),a.jdk_home.resolve(),a.catalog)
    a.output.write_text(json.dumps(r,indent=2)+'\n');print('Regional output candidate review passed:',a.output)
