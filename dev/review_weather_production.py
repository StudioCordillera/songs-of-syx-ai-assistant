"""Extend paired stored-reader review with production attribution and detached numeric checks."""
import argparse,hashlib,json,os,subprocess,sys,tempfile,zipfile
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from review_weather_candidate import review


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def verify(game,jdk,player):
    paired=review(game,jdk);audit=json.loads((ROOT/'api-audit.json').read_text())
    assert paired['game_jar_sha256']==audit['game_jar_sha256'] and paired['source_archive_sha256']==audit['source_archive_sha256']
    required={m['id'] for m in paired['public_route_members']}
    actual=[m for m in audit['members'] if m['id'] in required]
    assert len(actual)==len(required)==16 and all(m['public'] and len(m['source_candidates'])==1 for m in actual)
    state=Path(tempfile.mkdtemp(prefix='weather-production-contract-',dir=ROOT/'runtime'));classes=state/'classes';classes.mkdir()
    source=state/'WeatherPureCheck.java';source.write_text((ROOT/'dev/candidates/weather/WeatherPureCheck.java').read_text().replace('syx.assistant.candidate.WeatherObservation','syx.assistant.WeatherObservation'))
    java=['java','-Djava.home='+str(jdk.resolve())];cp=os.pathsep.join(map(str,[game/'SongsOfSyx.jar',player]))
    with zipfile.ZipFile(player) as z:assert 'syx/assistant/WeatherObservation.class' in z.namelist()
    subprocess.run([*java,'-m','jdk.compiler/com.sun.tools.javac.Main','--release','16','-cp',cp,'-d',str(classes),str(source)],check=True)
    result=subprocess.run(['java','-cp',cp+os.pathsep+str(classes),'WeatherPureCheck'],capture_output=True,text=True,check=True)
    assert result.stdout.strip()=='WEATHER PURE: accepted=3 rejected=58 no_game_initialization=true'
    names=['mod/src/main/java/syx/assistant/WeatherObservation.java','mod/src/main/java/syx/assistant/StateCollector.java','dev/review_weather_production.py','dev/review_weather_candidate.py']
    return {'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),'game_jar_sha256':paired['game_jar_sha256'],
        'source_archive_sha256':paired['source_archive_sha256'],'mod_jar_sha256':sha(player),'public_weather_members':actual,
        'paired_stored_reader_review':paired,'production_detached_checks':{'accepted':3,'rejected':58,'game_initializations':0},
        'source_sha256':{n:sha(ROOT/n) for n in names},
        'scope':'Selected stored accessors/source semantics plus actual production compiler attribution and detached shape checks. Field definitions add detached strings only; actual DTO/MCP/lifecycle acceptance is separate.',
        'limits':['Shipped-source/selected-bytecode verification, not separately documented stable official API contracts or complete source/binary equivalence.',
            'Native invalid stored factors/getter exceptions and broad climates/seasons remain unproven; public setter normalization is not fault injection.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['game-dir','jdk-home','mod-jar','output']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.output.write_text(json.dumps(verify(a.game_dir,a.jdk_home,a.mod_jar),indent=2)+'\n')
    print('Production weather source/bytecode attribution and detached checks passed without initializing a game.')
