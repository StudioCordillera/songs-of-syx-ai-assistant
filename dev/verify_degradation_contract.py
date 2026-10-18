"""Review producer-room degradation reads in shipped files; never initializes game classes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
from verify_bytecode import disassemble,method,fingerprint


def verify(game,jdk):
    jar=game/'SongsOfSyx.jar';archive=game/'info/SongsOfSyx-sources.jar'
    java=['java','-Djava.home='+str(jdk.resolve())]
    declarations=[
      ('settlement.room.main.RoomInstance','public double getDegrade();'),
      ('settlement.maintenance.ROOM_DEGRADER','public static double get(int);'),
      ('settlement.maintenance.MRoom','public static double degrade(int);'),
      ('snake2d.util.bit.Bits','public int get(int);'),
      ('settlement.room.home.chamber.ChamberInstance','public double getDegrade();'),
      ('settlement.room.main.construction.ConstructionInstance','public double getDegrade();')]
    checks=[];bodies=[]
    with zipfile.ZipFile(archive) as z:
        for owner,signature in declarations:
            body=method(disassemble(java,jar,owner),signature);bodies.append(body)
            name=owner.replace('.','/')+'.java';raw=z.read(name)
            checks.append({'owner':owner,'signature':signature,'source_path':name,
                'source_sha256':hashlib.sha256(raw).hexdigest(),'normalized_disassembly_sha256':fingerprint(body)})
        for body in bodies[:5]:
            assert not re.search(r'\b(putfield|putstatic|[abilfdcs]astore|new|newarray)\b',body)
        calls=[re.findall(r'// (?:InterfaceMethod|Method) ([^\n]+)',body) for body in bodies[:4]]
        assert len(calls[0])==len(calls[1])==len(calls[2])==1 and not calls[3],calls
        assert calls[0][0].endswith('Degrader.get:(I)D'),calls[0]
        assert calls[1]==['settlement/maintenance/MRoom.degrade:(I)D'],calls[1]
        assert calls[2]==['snake2d/util/bit/Bits.get:(I)I'],calls[2]
        assert 'putstatic' in bodies[5] and 'degI:' in bodies[5]
        overrides=[]
        for name in z.namelist():
            if name.endswith('.java'):
                raw=z.read(name);source=raw.decode(errors='replace')
                if re.search(r'(?:public|protected)\s+(?:final\s+)?double\s+getDegrade\s*\(\s*\)',source):
                    overrides.append({'source_path':name,'source_sha256':hashlib.sha256(raw).hexdigest()})
        assert {x['source_path'] for x in overrides}=={declarations[i][0].replace('.','/')+'.java' for i in [0,4,5]}
        chamber=z.read('settlement/room/home/chamber/ChamberInstance.java').decode()
        construction=z.read('settlement/room/main/construction/ConstructionInstance.java').decode()
        base=z.read('settlement/room/main/RoomInstance.java').decode()
        assert re.search(r'public final class ChamberInstance extends RoomInstance implements JOBMANAGER_HASER, HOME\s*\{',chamber)
        assert 'class ConstructionInstance extends Room.RoomInstanceImp implements ROOM_JOBBER' in construction
        assert 'public abstract class RoomInstance extends Room.RoomInstanceImp implements AREA' in base
        decoder=z.read('settlement/maintenance/MRoom.java').decode()
        assert 'new Bits(0b0000_0000_1111_1111_1111_1111_1111_0000)' in decoder
        for marker in ['min = tot.mask >> 2','1.0/(tot.mask -min)','double w = tot.get(data)',
                       'if (w > min)','w -= min','w*= II','return 0;']:assert marker in decoder,marker
        bits=z.read('snake2d/util/bit/Bits.java').decode()
        assert 'return (data >> scroll) & mask;' in bits
    return {'passed':True,'game_jar_sha256':hashlib.sha256(jar.read_bytes()).hexdigest(),
        'source_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
        'method':'Static source/binary review only; no game initialization, reflection, private runtime reads or maintenance calls.',
        'checks':checks,'getDegrade_declarations_in_shipped_source':overrides,
        'reviewed_base_decoder_is_thresholded_normalized_stored_value':True,
        'reviewed_base_reader_chain_has_no_write_opcode':True,
        'construction_sibling_delegate_mutation_is_outside_RoomInstance_producer_traversal':True,
        'chamber_final_nonproducer_override_not_used_by_production_mapping':True,
        'verifier_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'limits':['Scoped shipped-source/binary reader-chain review, not a formal purity proof or documented stable contract.',
          'Construction getter writes a delegate, and chamber getter represents a fixed working-state display. Neither is a producer RoomInstance mapped here.',
          'Zero from the base decoder can hide below-threshold stored wear. Exact last wear/maintenance time and resource cost are not established.',
          'Unknown third-party overrides may change behavior, meaning or cost. No runtime method discovery or arbitrary access is introduced.',
          'No complete production modifier, current output, forced-value, cap/fault or large-city acceptance.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['game-dir','jdk-home','output']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();report=verify(a.game_dir,a.jdk_home)
    a.output.write_text(json.dumps(report,indent=2)+'\n');print('Producer degradation getter chain and excluded overrides reviewed statically.')
