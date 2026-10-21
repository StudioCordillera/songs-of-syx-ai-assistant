"""Production housing attribution/body equivalence and pre-game budget checks; native acceptance separate."""
import argparse,hashlib,json,os,subprocess,sys,tempfile,zipfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from review_housing_boundary import review

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def verify(game,jdk,jar):
    paired=review(game,jdk);audit=json.loads((ROOT/'api-audit.json').read_text())
    assert paired['game_jar_sha256']==audit['game_jar_sha256'] and paired['source_archive_sha256']==audit['source_archive_sha256']
    candidate=ROOT/'dev/candidates/housing/syx/assistant/candidate/HousingObservation.java'
    production=ROOT/'mod/src/main/java/syx/assistant/HousingObservation.java'
    expected=candidate.read_text().replace('package syx.assistant.candidate;','package syx.assistant;').replace('/** Unregistered fixed public reader. Use only on GAME.addAfterUpdate; no engine handles escape. */','/** Fixed public housing reader on GAME.addAfterUpdate; no engine handle escapes. */')
    assert production.read_text()==expected,'Production reader algorithm differs from reviewed candidate'
    members=[m for m in audit['members'] if any(u.startswith('HousingObservation.java:') for u in m['uses'])]
    assert len(members)>=14 and all(m['public'] and len(m['source_candidates'])==1 for m in members)
    assert audit['mod_source_sha256']['syx/assistant/HousingObservation.java']==sha(production)
    with zipfile.ZipFile(jar) as z:assert 'syx/assistant/HousingObservation.class' in z.namelist() and not any('/candidate/' in n for n in z.namelist())
    state=Path(tempfile.mkdtemp(prefix='housing-production-contract-',dir=ROOT/'runtime'));classes=state/'classes';classes.mkdir()
    source=state/'HousingBudgetCheck.java';source.write_text('''import syx.assistant.HousingObservation;
public class HousingBudgetCheck {public static void main(String[] args){int n=0;
for(int b:new int[]{-1,0,10001,Integer.MAX_VALUE})try{HousingObservation.collect(b,1);throw new AssertionError();}catch(IllegalArgumentException ok){n++;}
for(int b:new int[]{-1,0,1001,Integer.MAX_VALUE})try{HousingObservation.collect(1,b);throw new AssertionError();}catch(IllegalArgumentException ok){n++;}
if(n!=8)throw new AssertionError();System.out.println("rejected=8 no_game_initialization=true");}}
''')
    java=['java','-Djava.home='+str(jdk.resolve())];cp=os.pathsep.join(map(str,[game/'SongsOfSyx.jar',jar]))
    subprocess.run([*java,'-m','jdk.compiler/com.sun.tools.javac.Main','--release','16','-cp',cp,'-d',str(classes),str(source)],check=True)
    result=subprocess.run(['java','-cp',cp+os.pathsep+str(classes),'HousingBudgetCheck'],capture_output=True,text=True,check=True)
    assert result.stdout.strip()=='rejected=8 no_game_initialization=true'
    names=['mod/src/main/java/syx/assistant/HousingObservation.java','mod/src/main/java/syx/assistant/StateCollector.java',
           'syx_housing.py','syx_mcp.py','dev/review_housing_production.py','dev/review_housing_boundary.py']
    return {'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),'game_jar_sha256':paired['game_jar_sha256'],'source_archive_sha256':paired['source_archive_sha256'],
      'mod_jar_sha256':sha(jar),'source_sha256':{n:sha(ROOT/n) for n in names},'reviewed_reader_body_unchanged_except_package_and_comment':True,
      'public_housing_collector_members':members,'paired_reader_source_review':paired,'production_bad_budget_rejections':8,'game_initializations':0,
      'scope':'Actual compiler attribution, fixed candidate-to-production reader-body equivalence and production bad-budget pre-game checks; not native/MCP/release acceptance.',
      'limits':['Public shipped-source/selected-bytecode verification, not separately documented stable housing contracts or complete source/binary equivalence.',
        'Detached relationship/definitions are derived outside the game thread once per decoded snapshot. Exact production DTO/MCP/chamber/fault/scene and cost/release gates are separate.',
        'Source counter meanings, failure/null scope, ID reuse, unavailable policy/resource-use actions and partial completeness retain the reviewed candidate restrictions.']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['game-dir','jdk-home','mod-jar','output']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.output.write_text(json.dumps(verify(a.game_dir,a.jdk_home,a.mod_jar),indent=2)+'\n')
    print('Production housing source/attribution and eight pre-game budget checks pass.')
