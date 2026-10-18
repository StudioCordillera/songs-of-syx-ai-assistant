"""Review stored production-period semantics without invoking game code.

Only hashes, anchors and conclusions are published. This does not add private
runtime access or decode the game's opaque production data arrays.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parent))
from verify_bytecode import disassemble,method,fingerprint


def verify(game,jdk):
    jar=game/'SongsOfSyx.jar';archive=game/'info/SongsOfSyx-sources.jar'
    java=['java','-Djava.home='+str(jdk)]
    owner='settlement.room.industry.module.consumption.RoomConsumptionAbs'
    binary=disassemble(java,jar,owner)
    rollover=method(binary,'public void updateRoom(settlement.room.industry.module.ROOM_IDATA_INSTANCE);')
    assert 'protected final util.data.INT_O$INT_OE<settlement.room.industry.module.ROOM_IDATA_INSTANCE> pday;' in binary
    cursor=0
    for marker in ['Field pday:', 'TIMECYCLE$Days.bitCurrent:', 'bipush        15', 'iand', 'if_icmpeq',
                   'TIMECYCLE$Days.bitsSinceStart:', 'TIMECYCLE$Years.bitConversion:', 'drem',
                   'IndustryResource.day:', 'DOUBLE_O$DOUBLE_OE.getD:', 'd2i', 'IndustryResource.dayPrev:',
                   'INT_O$INT_OE.set:', 'ineg', 'DOUBLE_O$DOUBLE_OE.incD:', 'IndustryResource.yearPrev:',
                   'IndustryResource.year:', 'INT_O$INT_OE.get:', 'INT_O$INT_OE.set:']:
        cursor=rollover.index(marker,cursor)+len(marker)
    assert rollover.count('IndustryResource.year:')==2
    float_read=method(disassemble(java,jar,'util.data.DataOSimple$DataFloat'),'public double getD(T);')
    assert 'DataOSimple$DataInt.get:' in float_read and 'Float.intBitsToFloat:' in float_read
    assert 'updateRoom:' not in float_read and not any(t in float_read for t in ('putfield','putstatic','.set:'))
    paths=['settlement/room/industry/module/consumption/RoomConsumptionAbs.java',
           'settlement/room/industry/module/IndustryResource.java','settlement/room/industry/module/ROOM_IDATA_INSTANCE.java',
           'util/data/DataOSimple.java']
    sources={}
    with zipfile.ZipFile(archive) as z:
        for path in paths:
            data=z.read(path);text=data.decode();sources[path]={'sha256':hashlib.sha256(data).hexdigest(),
                'anchors':[{ 'line':i,'kind':kind} for i,line in enumerate(text.splitlines(),1)
                    for token,kind in [('protected final INT_OE<ROOM_IDATA_INSTANCE> pday','protected_day_marker'),
                        ('public void updateRoom(','mutating_rollover'),('i.dayPrev.set','previous_day_write'),
                        ('i.day.incD','fractional_carry_preserved'),('i.yearPrev.set','previous_year_write'),
                        ('return Float.intBitsToFloat(dd.get(t))','float_read_no_rollover'),('long[] productionData()','opaque_storage_contract')]
                    if token in line]}
    return {'passed':True,'game_jar_sha256':hashlib.sha256(jar.read_bytes()).hexdigest(),
        'source_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
        'method':'Selected shipped-source and javap reference/control-flow review; no game execution, reflection or private runtime access. Not complete binary/source equivalence.',
        'source_evidence':sources,'binary_fingerprints':{'rollover':fingerprint(rollover),'float_getter':fingerprint(float_read)},
        'conclusions':[
            'Day rollover is a mutator guarded by a four-bit day marker, not performed by the public day float getter.',
            'Rollover copies the integer part of the day accumulator to the previous-day bucket and subtracts it, retaining the fractional remainder.',
            'Year rollover is conditional on a year-boundary test inside day rollover; the observer does not call this mutator.',
            'The marker is protected, not an established public exact-age getter. The opaque public productionData array does not document its layout or provide an age contract.',
            'previous_day_units labels a stored bucket, not independently verified calendar-yesterday output. Exact bucket age remains unavailable through the inspected public APIs.'],
        'limits':['Static review of these classes on the pinned game only; not a proof that no other public getter exists.',
            'No delayed/missed-day/year-rollover runtime fixture or full production forecast established.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game-dir',type=Path,required=True)
    p.add_argument('--jdk-home',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();report=verify(args.game_dir,args.jdk_home)
    args.output.write_text(json.dumps(report,indent=2)+'\n');print('Production-period source/binary review passed; exact bucket age remains unavailable.')
