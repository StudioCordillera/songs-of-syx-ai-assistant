"""Static review of public service-policy readers and configured/effective boundaries.

Reads licensed source/class archives, never initializes game classes. A private
implementation body is inspected as static evidence only; production invokes its
public returned interface and never names/casts that implementation.
"""
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
    java=['java','-Djava.home='+str(jdk.resolve())];jar=game/'SongsOfSyx.jar'
    declarations=[('settlement.room.service.module.RoomServiceAccess','public static snake2d.util.sets.LIST<settlement.room.service.module.RoomServiceAccess> ALL();','settlement/room/service/module/RoomServiceAccess.java'),
        ('settlement.room.service.module.RoomServiceAccess','public final settlement.stats.service.StatServiceRoom stats();','settlement/room/service/module/RoomServiceAccess.java'),
        ('settlement.stats.service.StatServiceImp','public util.data.BOOLEANO$BOOLEAN_OE<init.type.HCLASS_RACE> permission();','settlement/stats/service/StatServiceImp.java'),
        ('init.type.HCLASS_RACE','public static init.type.HCLASS_RACE clP(init.race.Race, init.type.HCLASS);','init/type/HCLASS_RACE.java'),
        ('settlement.stats.service.StatServiceImp$Perm','public boolean is(init.type.HCLASS_RACE);','settlement/stats/service/StatServiceImp.java')]
    checks=[]
    with zipfile.ZipFile(game/'info/SongsOfSyx-sources.jar') as archive:
        for owner,signature,path in declarations:
            body=method(disassemble(java,jar,owner),signature)
            assert not re.search(r'\b(putfield|putstatic|[abilfdcs]astore|new|newarray)\b',body),(owner,'reader writes/allocates')
            assert 'Bitmap1D.set:' not in body and 'permission.set:' not in body
            checks.append({'owner':owner,'signature':signature,'source_path':path,
                'source_sha256':hashlib.sha256(archive.read(path)).hexdigest(),
                'normalized_disassembly_sha256':fingerprint(body),'no_write_opcode_in_reviewed_reader':True,
                'static_implementation_only':owner.endswith('$Perm')})
        request=method(disassemble(java,jar,'settlement.stats.service.StatServiceImp'),'public boolean accessRequest(settlement.entity.humanoid.Humanoid);')
        for marker in ['HTYPES.NOBILITY:','HTYPES.TOURIST:','HTYPE.parent:','StandingDef.child:','HTYPE.parentClass:']:
            assert marker in request,marker
    return {'passed':True,'game_jar_sha256':hashlib.sha256(jar.read_bytes()).hexdigest(),
        'source_archive_sha256':hashlib.sha256((game/'info/SongsOfSyx-sources.jar').read_bytes()).hexdigest(),
        'method':'Static source/binary reader inspection. No game execution, private reflection or private-instance access.',
        'reader_checks':checks,'configured_is_not_effective_access':True,
        'effective_access_request_body_sha256':fingerprint(request),
        'source_review_conclusion':'Configured concrete cohort flag is read through public BOOLEAN_OE.is. Individual accessRequest also considers nobility/tourism and child/parent conditions. It is not invoked or reimplemented by production.',
        'limits':['No formal equivalence or stable official contract. No-write opcode checks are scoped static evidence, not a general purity proof.',
            'The private implementation is inspected in shipped files only; no runtime cast, reflection, bitmap access or policy setter exists in production.',
            'No full individual eligibility, reachability, service demand or permission-setter correctness established.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('game-dir','jdk-home','output'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();report=verify(args.game_dir,args.jdk_home)
    args.output.write_text(json.dumps(report,indent=2)+'\n');print('Service policy readers and configured/effective access distinction verified statically.')
