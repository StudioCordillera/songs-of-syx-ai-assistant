"""Selected public housing reader/source review; distinguishes stored ledgers from physical homes."""
import argparse,hashlib,json,re,sys,subprocess,os,tempfile,zipfile
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from verify_bytecode import disassemble,method,fingerprint
from review_stockpile_boundary import stored_reader


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def review(game,jdk):
    jar=game/'SongsOfSyx.jar';archive=game/'info/SongsOfSyx-sources.jar';catalog=json.loads((ROOT/'build/game-api-catalog.json').read_text())
    assert catalog['game_jar_sha256']==sha(jar) and catalog['source_archive_sha256']==sha(archive)
    ids={m['id']:m for m in catalog['members']}
    required=['settlement.room.main.RoomsMap#max()','settlement.room.main.RoomsMap#getByIndex(int)',
        'settlement.room.home.HOME#occupants()','settlement.room.home.HOME#occupantsMax()',
        'settlement.room.home.house.HomeInstance#occupants()','settlement.room.home.house.HomeInstance#occupantsOdd()',
        'settlement.room.home.house.HomeInstance#occupantsMax()','settlement.room.home.house.HomeInstance#occupant(int)',
        'settlement.room.home.house.HomeInstance#isolation()','settlement.room.home.house.ROOM_HOME#total(init.type.HGROUP)',
        'settlement.room.home.house.ROOM_HOME#used(init.type.HGROUP)','init.type.HGROUP#all()','init.type.HGROUP#index()',
        'settlement.room.home.chamber.ChamberInstance#occupants()','settlement.room.home.chamber.ChamberInstance#occupantsMax()']
    assert all(i in ids and 'public' in ids[i]['modifiers'] for i in required)
    java=['java','-Djava.home='+str(jdk.resolve())];checks=[]
    for owner,signature,markers in [
        ('settlement.room.home.house.HomeInstance','public int occupants();',('am:B','ireturn')),
        ('settlement.room.home.house.HomeInstance','public int occupantsOdd();',('amOdd:B','ireturn')),
        ('settlement.room.home.house.HomeInstance','public double isolation();',('isolation:B','dreturn')),
        ('settlement.room.home.chamber.ChamberInstance','public int occupantsMax();',('iconst_1','ireturn')),
        ('init.type.HGROUP','public int index();',('index:I','ireturn')),
    ]:
        code=method(disassemble(java,jar,owner),signature);stored_reader(code,markers)
        assert not re.search(r'\binvoke\w*\b',code)
        checks.append({'owner':owner,'signature':signature,'normalized_disassembly_sha256':fingerprint(code),'scope':'Selected stored/constant accessor body; no calls, direct writes, allocation or backward branch.'})
    for name in ['total','used']:
        code=method(disassemble(java,jar,'settlement.room.home.house.ROOM_HOME'),f'public int {name}(init.type.HGROUP);')
        stored_reader(code,(name+'T:I',name+':[I','init/type/HGROUP.index:()I','iaload'))
        invocations=[l for l in code.splitlines() if re.search(r'\binvoke\w*\b',l)]
        assert len(invocations)==1 and 'HGROUP.index:()I' in invocations[0]
        checks.append({'owner':'settlement.room.home.house.ROOM_HOME','signature':name+'(HGROUP)',
            'normalized_disassembly_sha256':fingerprint(code),'scope':'Null returns stored group-sum scalar; nonnull indexes stored group array through separately checked HGROUP.index.'})
    exclusions=[]
    for owner,signature,markers in [
        ('settlement.room.home.house.HomeInstance','public int resourceAm(int);',('resCount:',)),
        ('settlement.room.home.house.HomeInstance','private void resCount();',('unuse:', 'putfield')),
        ('settlement.room.home.house.HomeInstance','public settlement.room.home.HOME use();',('litTimer:', 'putfield')),
        ('settlement.room.home.house.OddHome','public boolean has(settlement.entity.humanoid.Humanoid);',('poll:','test:')),
    ]:
        code=method(disassemble(java,jar,owner),signature);assert all(m in code for m in markers)
        exclusions.append({'owner':owner,'signature':signature,'normalized_disassembly_sha256':fingerprint(code),'reason':'Can mutate persistent state/cache, lighting or search queue; excluded from observer.'})
    files=['settlement/room/home/HOME.java','settlement/room/home/house/HomeInstance.java','settlement/room/home/house/ROOM_HOME.java',
        'settlement/room/home/house/OddHome.java','settlement/room/home/house/HomeContructor.java','settlement/room/home/chamber/ChamberInstance.java',
        'settlement/room/home/chamber/ROOM_CHAMBER.java','settlement/room/home/chamber/Constructor.java','settlement/room/main/Room.java',
        'settlement/room/main/RoomInstance.java','settlement/room/main/MapDataF.java','settlement/room/main/furnisher/Furnisher.java',
        'settlement/room/main/furnisher/FurnisherItemGroup.java','init/type/HGROUP.java','settlement/stats/colls/StatsHome.java']
    with zipfile.ZipFile(archive) as z:hashes={n:hashlib.sha256(z.read(n)).hexdigest() for n in files}
    candidate=ROOT/'dev/candidates/housing/syx/assistant/candidate/HousingObservation.java'
    state=Path(tempfile.mkdtemp(prefix='housing-contract-',dir=ROOT/'runtime'));player=state/'player.jar';classes=state/'classes';classes.mkdir()
    with zipfile.ZipFile(ROOT/'releases/latest-user-test.zip') as z:player.write_bytes(z.read('mod/syx-ai-assistant/V71/script/syx-ai-assistant.jar'))
    pure=state/'HousingBudgetCheck.java';pure.write_text('''import syx.assistant.candidate.HousingObservation;
public class HousingBudgetCheck {public static void main(String[] x){int n=0;
for(int bad:new int[]{-1,0,10001,Integer.MAX_VALUE})try{HousingObservation.collect(bad,1);throw new AssertionError();}catch(IllegalArgumentException ok){n++;}
for(int bad:new int[]{-1,0,1001,Integer.MAX_VALUE})try{HousingObservation.collect(1,bad);throw new AssertionError();}catch(IllegalArgumentException ok){n++;}
if(n!=8)throw new AssertionError();System.out.println("rejected=8 no_game_initialization=true");}}
''')
    cp=os.pathsep.join(map(str,[jar,player]));subprocess.run([*java,'-m','jdk.compiler/com.sun.tools.javac.Main','--release','16','-cp',cp,'-d',str(classes),str(candidate),str(pure)],check=True)
    result=subprocess.run(['java','-cp',cp+os.pathsep+str(classes),'HousingBudgetCheck'],capture_output=True,text=True,check=True)
    assert result.stdout.strip()=='rejected=8 no_game_initialization=true'
    return {'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),'game_jar_sha256':sha(jar),'source_archive_sha256':sha(archive),
        'public_route_members':[{'id':i,'source_anchor':ids[i]['source_candidates']} for i in required],
        'selected_source_sha256':hashes,'selected_reader_checks':checks,'excluded_routes':exclusions,
        'external_candidate_compilation':True,'detached_budget_rejections':8,'game_initializations':0,
        'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [candidate,Path(__file__)]},
        'manual_semantic_review':['Ordinary homes are persistent HomeInstance room slots, distinct from RoomInstance employee/producer tables. Capacity follows furnishing-group/upgrade lookup through public pure stored accessors; service coordinates are door/service identity, not UI selection.',
            'HomeInstance.occupants is a stored assigned count; occupantsOdd is stored no-employment-at-accounting bookkeeping, not an up-to-date unemployment census. Availability uses am-amOdd and may admit a replacement even when the physical roster is full.',
            'ChamberInstance.occupants resolves its recorded entity ID to report zero/one. Zero does not prove its private raw ID slot is zero. Its capacity is constant one. These two home kinds must keep different count provenance.',
            'ROOM_HOME.report adds counters once per eligible cohort bit; null total/used sums these cohort ledgers. Empty homes can therefore contribute to multiple cohorts. Neither null totals nor sum(cohort capacity-used) is a unique physical vacancy count.',
            'Ordinary isolation is an unsigned eight-bit fraction. Chamber isolation delegates to conditional RoomInstance isolation and may return one when its constructor does not require indoors; not complete housing quality or fresh environmental measurement.',
            'HomeInstance.resourceAm calls resCount/unuse and can refresh resourceData/renderTimer or lighting. use, occupy/vacate, settingSet, upgradeSet and OddHome search queue methods are excluded.',
            'Policy-bit getters can lazily allocate/resize backing data and occupied-home availability can initialize specific-group caches; no policy handle or eligibility evaluation is exposed by this candidate.',
            'Existing hCoo is a public reusable scratch coordinate. A native fixture may immediately copy/check it against a home service coordinate; no scratch or HOME/room/entity handle crosses a DTO boundary.'],
        'limits':['Selected shipped-source/bytecode/accessibility checks, not separately documented stable official housing contracts or whole call-graph equivalence.',
            'Manual transitive review covers fixed known concrete home/chamber/furnisher/map/index routes; no generic HOME implementation or arbitrary invocation is accepted.',
            'No native/MCP/player acceptance follows from this static verifier. Candidate remains unregistered; two known home types only.',
            'Rows/slots/cohorts/resident IDs have finite caps; failure/truncation qualify absence. No physical presence, effective reachability, permanent room identity or exact counter age claim.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['game-dir','jdk-home','output']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.output.write_text(json.dumps(review(a.game_dir,a.jdk_home),indent=2)+'\n')
    print('Housing public source/selected-bytecode and detached budget review passed without initializing a game.')
