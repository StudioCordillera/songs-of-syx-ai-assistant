"""Cross-language detached gesture traces; no game, native input, provider or player integration."""
import argparse,hashlib,json,math,os,random,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from dev.chat_gesture_candidate import GestureCandidate,Rect


def trace_corpus():
    lines=[];checks={}
    def add(line,expected=None):
        if expected is not None:checks[len(lines)]=expected
        lines.append(line)
    begin='B\tlauncher\t50\t50\t0\t40\t40\t44\t44\t1280\t960'
    def sample(x,y,t,held='true',active='true',w=1280,h=960):return f'S\t{x}\t{y}\t{t}\t{held}\t{active}\t{w}\t{h}'
    add(begin);add(sample(50,50,100,'false'),('toggle',(40,40,44,44)))
    add(begin);add(sample(50,50,350),('armed',(40,40,44,44)));add(sample(50,50,400,'false'),('released',(40,40,44,44)))
    add(begin);add(sample(55,55,100),('blocked',(40,40,44,44)));add(sample(50,50,400),('blocked',(40,40,44,44)));add(sample(80,80,450,'false'),('released',(40,40,44,44)))
    add('B\theader\t50\t50\t0\t40\t40\t600\t500\t1280\t960');add(sample(51,51,1),('dragging',(41,41,600,500)));add(sample(52,52,2,'false'),('dropped',(42,42,600,500)))
    add(begin);add(sample(50,50,350));add(sample(1280,960,400),('dragging',(1236,916,44,44)));add(sample(1280,960,410,'false'),('dropped',(1236,916,44,44)))
    add(begin);add(sample('NaN',50,100),('error',None));add(sample(50,50,25),('holding',(40,40,44,44)))
    add(sample(50,50,300,w=-1),('error',None));add(sample(50,50,26),('holding',(40,40,44,44)));add('C')
    add('B\tgame\t50\t50\t0\t40\t40\t44\t44\t1280\t960',('error',None));add(sample(50,50,1,'false'),('idle',None))
    add(begin);add(sample(50,50,30,'1'),('error',None));add(sample(50,50,10,'false'),('toggle',(40,40,44,44)))
    for reason in ['outside','inactive','timeout','viewport']:
        add(begin)
        values={'outside':sample(-1,50,10),'inactive':sample(50,50,10,active='false'),'timeout':sample(50,50,5000),'viewport':sample(50,50,10,w=800)}
        add(values[reason],('cancelled',None));add(sample(50,50,6000,'false'),('idle',None))
    # Deliberately finite small/desktop-sized cases, not physical scaling acceptance or exhaustive doubles.
    randomizer=random.Random(482971)
    for _ in range(200):
        add('C');target=randomizer.choice(['launcher','header','chrome','resize'])
        w=randomizer.randint(80,2200);h=randomizer.randint(60,1300)
        rw=randomizer.randint(20,800);rh=randomizer.randint(20,700);rx=randomizer.randint(-40,w);ry=randomizer.randint(-40,h)
        rect=Rect(rx,ry,rw,rh).fit(w,h);x=rect.x+rect.width/2;y=rect.y+rect.height/2
        add(f'B\t{target}\t{x}\t{y}\t0\t{rx}\t{ry}\t{rw}\t{rh}\t{w}\t{h}')
        at=0
        for _ in range(8):
            at+=randomizer.randint(1,800)
            px=randomizer.randint(-2,w+2);py=randomizer.randint(-2,h+2)
            add(sample(px,py,at,'true' if randomizer.random()<.8 else 'false','true' if randomizer.random()<.97 else 'false',w,h))
    return lines,checks


def python_trace(lines):
    model=GestureCandidate();out=[]
    def flag(value):
        if value not in ('true','false'):raise ValueError('Boolean required')
        return value=='true'
    for line in lines:
        p=line.split('\t')
        try:
            if p[0]=='B' and len(p)==11:
                r=model.begin(p[1],float(p[2]),float(p[3]),float(p[4]),Rect(*map(float,p[5:9])),tuple(map(float,p[9:11])));status='began'
            elif p[0]=='S' and len(p)==8:
                status,r=model.sample(float(p[1]),float(p[2]),float(p[3]),held=flag(p[4]),surface_active=flag(p[5]),viewport=tuple(map(float,p[6:8])))
            elif p==['C']:status,r=model.cancel()
            else:raise ValueError('Fixed trace shape required')
            out.append((status,None if r is None else (r.x,r.y,r.width,r.height)))
        except (ValueError,OverflowError):out.append(('error',None))
    return out


def verify(directory):
    directory=directory.resolve();directory.mkdir(parents=True,exist_ok=True)
    lines,expected=trace_corpus();reference=python_trace(lines)
    for index,result in expected.items():assert reference[index]==result,(index,reference[index],result)
    raw=('\n'.join(lines)+'\n').encode('ascii');(directory/'gesture-traces.tsv').write_bytes(raw)
    classes=directory/'classes';classes.mkdir(exist_ok=True)
    compiler=['java']
    if os.environ.get('SYX_JAVA_HOME'):compiler+=['-Djava.home='+os.environ['SYX_JAVA_HOME']]
    sources=[ROOT/'dev/java/syx/assistant/candidate'/n for n in ['GestureReducer.java','GestureTrace.java']]
    subprocess.run([*compiler,'-m','jdk.compiler/com.sun.tools.javac.Main','--release','16','-encoding','UTF-8','-d',str(classes),*map(str,sources)],check=True,capture_output=True,text=True)
    result=subprocess.run(['java','-cp',str(classes),'syx.assistant.candidate.GestureTrace'],input=raw,capture_output=True,check=True,timeout=30)
    received=result.stdout.decode('ascii').splitlines();assert len(received)==len(reference)
    for index,(line,wanted) in enumerate(zip(received,reference)):
        fields=line.split('\t');actual=(fields[0],None if fields[1:]==['-'] else tuple(map(float,fields[1:])))
        assert actual[0]==wanted[0] and (actual[1] is None)==(wanted[1] is None),(index,actual,wanted)
        if actual[1] is not None:
            assert len(actual[1])==4 and all(math.isclose(a,b,abs_tol=1e-9,rel_tol=1e-12) for a,b in zip(actual[1],wanted[1])),(index,actual,wanted)
    names=['dev/chat_gesture_candidate.py','dev/verify_gesture_reducer.py','test_chat_gesture_candidate.py','test_gesture_reducer_java.py',*map(lambda p:str(p.relative_to(ROOT)),sources)]
    report={'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),
      'scope':'Unshipped game-independent Java gesture reducer, reconciled with accepted browser interaction policies; finite Python/Java trace parity, not native adapter acceptance.',
      'trace_steps':len(lines),'independently_authored_expected_steps':len(expected),'seeded_gesture_scenarios':200,'java_release_target':16,
      'trace_sha256':hashlib.sha256(raw).hexdigest(),'java_response_sha256':hashlib.sha256(result.stdout).hexdigest(),
      'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},
      'game_calls':0,'native_input_calls':0,'provider_calls':0,'production_integration':False,
      'limits':['Detached primitives and own-surface labels are supplied by the test; native hit testing, pointer ownership, window focus/capture/loss, coordinate scaling and scene integration are not established.',
        'Launcher hold threshold uses supplied monotonic samples, not browser timer ordering. Immediate nonzero own header/chrome/resize movement, early-move lockout and stationary engaged-hold suppression are policy choices; not full browser/native equivalence.',
        'Five-second cancellation is a recovery policy, not focus proof. Minimum layout size remains480x320 shrinking at viewport edges; native font, clipping, themes, persistence and accessibility are separate gates.',
        'Only controlled trace input and finite desktop/small geometry ranges are evaluated; test framing is not a production IPC or general adversarial-stream parser.',
        'No native drag/resize, target chip, badge, receipt or gameplay action is shipped. Existing player JAR/helper/download validation remains separate.']}
    (directory/'gesture-reducer-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True)
    result=verify(p.parse_args().output_dir)
    print('Detached Java/Python gesture traces passed:',result['trace_steps'],'steps;',result['independently_authored_expected_steps'],'independent expected steps')
