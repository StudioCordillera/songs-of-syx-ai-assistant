"""Static source/binary review of the three public service counter readers.

Reads licensed archives without initializing game classes. Publishes metadata and
conclusions only; no proprietary method bodies or save values.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import sys
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parent))
from verify_bytecode import disassemble,method,fingerprint


def verify(game,jdk):
    java=['java','-Djava.home='+str(jdk.resolve())]
    binary=disassemble(java,game/'SongsOfSyx.jar','settlement.room.service.module.RoomServiceInstance')
    checks=[];dispatch=[]
    with zipfile.ZipFile(game/'info/SongsOfSyx-sources.jar') as source:
        name='settlement/room/service/module/RoomServiceInstance.java'
        raw=source.read(name);text=raw.decode()
        for getter in ['available','total','reserved']:
            signature='public int '+getter+'();'
            body=method(binary,signature)
            instructions=[line.split(':',1)[1].strip() for line in body.splitlines() if line.strip() and line.strip().split(':',1)[0].isdigit()]
            assert len(instructions)==3,(getter,'changed getter body')
            assert instructions[0]=='aload_0' and instructions[1].startswith('getfield ') and instructions[2]=='ireturn'
            assert '// Field '+getter+':S' in instructions[1]
            anchor=next(i+1 for i,line in enumerate(text.splitlines()) if 'int '+getter+'()' in line)
            checks.append({'member':'RoomServiceInstance#'+getter+'()', 'passed':True,'source_path':name,'source_line':anchor,
                'source_sha256':hashlib.sha256(raw).hexdigest(),'normalized_disassembly_sha256':fingerprint(body),
                'conclusion':'Public getter returns its stored short counter directly; no refresh, report, reservation or other call.'})
        # Scope this source scan to concrete no-argument declarations returning
        # exactly RoomServiceInstance; this is not an inheritance completeness proof.
        for path in source.namelist():
            if not path.endswith('.java'):continue
            raw=source.read(path);text=raw.decode('utf-8-sig')
            for match in re.finditer(r'public\s+(?:final\s+)?RoomServiceInstance\s+service\s*\(\s*\)\s*\{([^}]*)\}',text):
                body=' '.join(match.group(1).split())
                assert re.fullmatch(r'return \w+;',body),(path,'changed service reader')
                dispatch.append({'source_path':path,'source_line':text[:match.start()].count('\n')+1,
                    'source_sha256':hashlib.sha256(raw).hexdigest(),
                    'reader_body_sha256':hashlib.sha256(body.encode()).hexdigest()})
        assert len(dispatch)==24,'Re-review the installed concrete service readers'
    return {'passed':True,'game_jar_sha256':hashlib.sha256((game/'SongsOfSyx.jar').read_bytes()).hexdigest(),
        'shipped_source_jar_sha256':hashlib.sha256((game/'info/SongsOfSyx-sources.jar').read_bytes()).hexdigest(),
        'method':'Static JDK disassembly and shipped-source anchor review. No game method execution.', 'checks':checks,
        'concrete_service_readers_source_scan':{'count':len(dispatch),'all_simple_stored_returns':True,'declarations':dispatch},
        'limits':['Three counter getter bodies and 24 matching concrete service readers; not formal source/binary equivalence or a documented stable API contract.',
            'The concrete source scan matches explicit public RoomServiceInstance service() declarations; it is not exhaustive inheritance/mod compatibility analysis.',
            'Stored counters have room-specific meaning; this check does not prove daily capacity, demand, accessibility or refresh age.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('game-dir','jdk-home','output'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();report=verify(args.game_dir,args.jdk_home)
    args.output.write_text(json.dumps(report,indent=2)+'\n');print('Three public service counter readers verified as direct stored reads.')
