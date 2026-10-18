"""Static review only. Never initializes or invokes game code, including private helpers."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
from verify_bytecode import disassemble,method,fingerprint


def review(game,jdk):
    jar=game/'SongsOfSyx.jar';archive=game/'info/SongsOfSyx-sources.jar'
    java=['java','-Djava.home='+str(jdk.resolve())]
    declarations=[
      ('settlement.room.industry.module.IndustryUtil','public static double calcProductionRate(double, settlement.room.industry.module.IndustryRate, game.boosting.Boostable, settlement.room.main.RoomInstance);'),
      ('settlement.room.main.employment.RoomEmploymentIns','public static snake2d.util.sets.LIST<settlement.entity.humanoid.Humanoid> employees(settlement.room.main.RoomInstance);'),
      ('settlement.room.main.employment.RoomEmploymentIns','private static boolean echeck(java.lang.Object);'),
      ('settlement.room.main.employment.RoomEmploymentIns','public static snake2d.util.sets.LIST<settlement.entity.humanoid.Humanoid> employees(settlement.room.main.RoomInstance, snake2d.util.sets.LISTE<settlement.entity.humanoid.Humanoid>);'),
      ('settlement.room.industry.module.IndustryUtil','public static double roomBonus(settlement.room.main.RoomInstance, settlement.room.industry.module.IndustryRate);'),
      ('settlement.room.main.RoomInstance','public double getDegrade();'),
      ('settlement.maintenance.ROOM_DEGRADER','public static double get(int);'),
      ('settlement.maintenance.MRoom','public static double degrade(int);')]
    bodies=[];checks=[]
    with zipfile.ZipFile(archive) as z:
        for owner,signature in declarations:
            body=method(disassemble(java,jar,owner),signature);bodies.append(body)
            path=owner.replace('.','/')+'.java'
            checks.append({'owner':owner,'signature':signature,'source_path':path,
                'source_sha256':hashlib.sha256(z.read(path)).hexdigest(),
                'normalized_disassembly_sha256':fingerprint(body),
                'static_inspection_only':True})
        assert 'RoomEmploymentIns.employees:()' in bodies[0] and 'Boostable.get:' in bodies[0]
        assert 'employed:()' not in bodies[0], 'The reviewed helper has no employed-count multiplication'
        assert 'echeck:' in bodies[1] and 'employees:' in bodies[1]
        for marker in ['putstatic','employeesI:','employeesO:','clearSoft:']:assert marker in bodies[2],marker
        assert 'getAllEnts:' in bodies[3] and 'hasRoom:' in bodies[3]
        assert 'RoomBoost.get:' in bodies[4] and 'getDegrade:' in bodies[4]
        source=z.read('settlement/room/industry/module/IndustryUtil.java').decode()
        assert re.search(r'if\s*\(am > 0\).*?mul /= am;.*?else\s*\{\s*mul = 1;',source,re.S)
        for body in bodies[5:]:assert not re.search(r'\b(putfield|putstatic|[abilfdcs]astore|new|newarray)\b',body)
    return {'passed':True,'game_jar_sha256':hashlib.sha256(jar.read_bytes()).hexdigest(),
        'source_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'method':'Static source/binary review; no game execution, reflection or private runtime access.',
        'checks':checks,
        'conclusions':[
          'Room-average production helper evaluates dynamic boosts and per-person bonus reads, averages employees and defaults the average to one without employees. It is not a measured room total or output forecast.',
          'Employee enumeration uses a shared cache keyed by update/object; its private cache check writes static cache metadata and clears the shared list. Population traversal stops at list capacity and has no observer-supplied scan bound.',
          'Generic roomBonus dispatches RoomBoost.get. A public interface alone does not establish the purity, units or cost of every implementation.',
          'RoomInstance.getDegrade is a narrower public candidate: the reviewed stored-decoder chain has no write opcode. It is not yet mapped or runtime-validated by this checkpoint.'],
        'verifier_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'limits':['Scoped call-site/source review, not complete call-graph equivalence or a general purity proof.',
          'Private helpers and a package implementation are inspected only in shipped files, never called by the mod or fixture.',
          'No new game getters, full modifier stack, cost bound, present productivity, large-city or all-menu acceptance.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['game-dir','jdk-home','output']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();r=review(a.game_dir,a.jdk_home);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print('Production helper boundaries reviewed without game execution.')
