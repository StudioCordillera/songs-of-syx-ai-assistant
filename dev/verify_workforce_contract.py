"""Review the pinned public workforce readers statically, without loading game classes."""
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
    declarations=[('settlement.room.main.employment.RoomEmploymentIns',n) for n in
        ['efficiency','proximity','fetchProximity','totEfficiency']]
    declarations.append(('settlement.room.main.employment.RoomEmploymentSimple','countInput'))
    checks=[]
    with zipfile.ZipFile(archive) as z:
        source=z.read('settlement/room/main/employment/RoomEmploymentIns.java').decode()
        # Reporting/reset paths are inspected but never invoked by production.
        for marker in ['lastProximity = 100;','lastFetch = 100;','EffLast = 100;',
                       '0.5*EffLast + 0.5*next','0.75*p + 0.25*lastFetch/100.0']:
            assert marker in source,marker
        for owner,name in declarations:
            signature='public '+('boolean' if name=='countInput' else 'double')+' '+name+'();'
            body=method(disassemble(java,jar,owner),signature)
            assert not re.search(r'\b(putfield|putstatic|[abilfdcs]astore|new|newarray)\b',body),(name,'reader writes/allocates')
            if name!='totEfficiency':assert not re.search(r'\binvoke\w*\b',body),(name,'unexpected reader call')
            else:
                for marker in ['efficiency:()D','proximity:()D','fetchProximity:()D','RoomEmploymentSimple.countInput:()Z']:
                    assert marker in body,marker
                assert len(re.findall(r'\bdmul\b',body))==2
                assert re.search(r'\bifeq\b',body),'Fetch multiplication must stay conditional'
                # Pin the small current call surface rather than treating no-write as a general purity proof.
                calls=re.findall(r'// (?:InterfaceMethod|Method) ([^\n]+)',body)
                assert len(calls)==6,calls
                allowed=['efficiency:()D','proximity:()D','fetchProximity:()D',
                    'settlement/room/main/RoomInstance.blueprintI:()Lsettlement/room/main/RoomBlueprintIns;',
                    'settlement/room/main/RoomBlueprintIns.employment:()Lsettlement/room/main/employment/RoomEmploymentSimple;',
                    'settlement/room/main/employment/RoomEmploymentSimple.countInput:()Z']
                assert set(calls)==set(allowed),calls
            path=owner.replace('.','/')+'.java';raw=z.read(path)
            checks.append({'owner':owner,'signature':signature,'source_path':path,
                'source_sha256':hashlib.sha256(raw).hexdigest(),'normalized_disassembly_sha256':fingerprint(body),
                'no_write_opcode_in_reviewed_reader':True})
    return {'passed':True,'game_jar_sha256':hashlib.sha256(jar.read_bytes()).hexdigest(),
        'source_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
        'method':'Static source/binary inspection of five public readers. No game class initialization, reflection, private runtime reads or reporting/reset calls.',
        'reader_checks':checks,'combined_fetch_factor_is_conditional':True,'stored_values_can_be_smoothed_or_reset':True,
        'limits':['Scoped reader/call-surface review, not formal purity/equivalence or an official stable mod contract.',
            'Getters return stored factors without an observation timestamp. Exact age remains unknown; defaults/resets can appear on inactive or unstaffed rooms.',
            'Not a complete production modifier, per-worker productivity percentage, input-supply test or throughput forecast.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['game-dir','jdk-home','output']:p.add_argument('--'+n,type=Path,required=True)
    args=p.parse_args();report=verify(args.game_dir,args.jdk_home)
    args.output.write_text(json.dumps(report,indent=2)+'\n');print('Workforce reader contract reviewed statically.')
