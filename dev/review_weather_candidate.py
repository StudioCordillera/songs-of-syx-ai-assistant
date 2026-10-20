"""Pair fixed public stored-weather readers with shipped source/bytecode and detached shape checks."""
import argparse
from datetime import datetime,timezone
import hashlib,json,os,re,subprocess,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from verify_bytecode import disassemble,method,fingerprint
from review_stockpile_boundary import stored_reader


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def review(game,jdk):
    jar=game/'SongsOfSyx.jar';archive=game/'info/SongsOfSyx-sources.jar';catalog=json.loads((ROOT/'build/game-api-catalog.json').read_text())
    assert catalog['game_jar_sha256']==sha(jar) and catalog['source_archive_sha256']==sha(archive)
    ids={m['id']:m for m in catalog['members']};fields=['moisture','snow','ice','wind','temp','clouds','rain','thunder','growth','growthRipe']
    required=['settlement.main.SETT#WEATHER()','settlement.weather.WeatherThing#getD()',*[f'settlement.weather.SWEATHER#{f}' for f in fields],
        'settlement.weather.WeatherSnow#rainIsSnow()','settlement.weather.WeatherGrowth#isAutumn()',
        'settlement.weather.WeatherGrowthRipe#cropsAreRipe()','settlement.weather.WeatherGrowthRipe#ripening()']
    assert all(i in ids and 'public' in ids[i]['modifiers'] for i in required)
    java=['java','-Djava.home='+str(jdk.resolve())];checks=[]
    for owner,signature,markers in [
        ('settlement.main.SETT','public static settlement.weather.SWEATHER WEATHER();',('weather:', 'areturn')),
        ('settlement.weather.WeatherThing','public double getD();',('d:D','dreturn')),
        ('settlement.weather.WeatherSnow','public boolean rainIsSnow();',('snowCount:D','ireturn')),
        ('settlement.weather.WeatherGrowth','public boolean isAutumn();',('isAutumn:Z','ireturn')),
        ('settlement.weather.WeatherGrowthRipe','public boolean cropsAreRipe();',('ripe:Z','ireturn')),
        ('settlement.weather.WeatherGrowthRipe','public boolean ripening();',('ripening:Z','ireturn'))]:
        code=method(disassemble(java,jar,owner),signature);stored_reader(code,markers)
        assert not re.search(r'\binvoke\w*\b',code)
        checks.append({'owner':owner,'signature':signature,'normalized_disassembly_sha256':fingerprint(code),
            'scope':'Selected stored accessor body; no calls, direct writes, allocation or backward branch.'})
    types=['WeatherMoisture','WeatherSnow','WeatherIce','WeatherWind','WeatherTemp','WeatherClouds','WeatherDownfall','WeatherThunder','WeatherGrowth','WeatherGrowthRipe']
    source_files={}
    with zipfile.ZipFile(archive) as z:
        for name in ['SWEATHER','WeatherThing',*types]:
            n='settlement/weather/'+name+'.java';source_files[n]=hashlib.sha256(z.read(n)).hexdigest()
        for name in types:
            code=disassemble(java,jar,'settlement.weather.'+name)
            assert 'public final class settlement.weather.'+name in code and not re.search(r'^  public double getD\(\);$',code,re.M)
    state=Path(tempfile.mkdtemp(prefix='weather-contract-',dir=ROOT/'runtime'));player=state/'player.jar';classes=state/'classes';classes.mkdir()
    with zipfile.ZipFile(ROOT/'releases/latest-user-test.zip') as z:player.write_bytes(z.read('mod/syx-ai-assistant/V71/script/syx-ai-assistant.jar'))
    with zipfile.ZipFile(player) as z:assert 'syx/assistant/candidate/WeatherObservation.class' not in z.namelist()
    candidate=ROOT/'dev/candidates/weather/syx/assistant/candidate/WeatherObservation.java';pure=ROOT/'dev/candidates/weather/WeatherPureCheck.java'
    cp=os.pathsep.join(map(str,[jar,player]));subprocess.run([*java,'-m','jdk.compiler/com.sun.tools.javac.Main','--release','16','-cp',cp,'-d',str(classes),str(candidate),str(pure)],check=True)
    result=subprocess.run(['java','-cp',cp+os.pathsep+str(classes),'WeatherPureCheck'],check=True,capture_output=True,text=True)
    assert result.stdout.strip()=='WEATHER PURE: accepted=3 rejected=58 no_game_initialization=true'
    return {'passed':True,'checked_at':datetime.now(timezone.utc).isoformat(),'game_jar_sha256':sha(jar),'source_archive_sha256':sha(archive),
        'public_route_members':[{'id':i,'source_anchor':ids[i]['source_candidates']} for i in required],
        'selected_source_sha256':source_files,'checks':checks,'concrete_final_classes_inheriting_stored_getD':types,
        'detached_shape_checks':{'accepted':3,'rejected':58,'game_initializations':0},
        'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [candidate,pure,Path(__file__)]},
        'conclusions':['Ten fixed public final weather components inherit the stored double getter; four flags read stored booleans or a stored snow-history sign. No mutable handle or generic invocation is returned.',
            'WeatherThing setters clamp values but loading restores the raw saved double without validation. Candidate refuses nonfinite/out-of-range factors instead of normalizing them into invented values.',
            'Precipitation history differs from current downfall and from per-tile ground moisture; temperature is a game scale, not a physical temperature conversion.',
            'Growth/ripeness are global stored factors, not individual crop yields. GrowthRipe.update computes cached ripe/ripening flags using the prior getD before storing the new seasonal factor; flags must not be re-derived as simultaneous truth.',
            'Moisture.setD can send a drought message; weather updates, setters, targets, renderer/light/audio handles and forecast calculations are excluded.'],
        'limits':['Shipped-source/selected-bytecode verification and external compiler access, not separately documented stable official mod contracts or complete source/binary equivalence.',
            'No native weather or MCP/player acceptance follows from this static check. Native evidence is separate; candidate remains unregistered.',
            'Ten factors and four flags only; no regional weather map, exact cache age, normal physical units, crop productivity or forecast.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['game-dir','jdk-home','output']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.output.write_text(json.dumps(review(a.game_dir,a.jdk_home),indent=2)+'\n')
    print('Stored public weather candidate review and detached checks passed without initializing a game.')
