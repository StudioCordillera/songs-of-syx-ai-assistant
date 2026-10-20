"""Python -> Java frame corpus and Java -> Python receipt; no game dependencies."""
import base64
import os
from pathlib import Path
import subprocess
from uuid import uuid4
from dev.chat_display_candidate import DisplayBroker
from syx_chat_store import ChatStore

ROOT=Path(__file__).resolve().parent


def final(store,chat,text='Answer'):
    tid=str(uuid4());cid=chat['chat_id'];session=chat['attached_session']
    store.begin(cid,tid,session,'Question')
    store.append(cid,tid,session,'assistant',dict(text=text,completed=True));store.finish(cid,tid,'completed')


def replace_field(raw,key,value):
    return ('\n'.join(key+'='+value if line.startswith(key+'=') else line for line in raw.decode('ascii').splitlines())+'\n').encode('ascii')


def test_shared_display_corpus_and_java_receipt_round_trip(tmp_path):
    store=ChatStore(tmp_path/'history');session=str(uuid4())
    chat=store.new(session,model='deepseek-v4-pro');cid=chat['chat_id']
    broker=DisplayBroker(store,epoch='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa');broker.history.initialize()
    corpus=[]
    def accept(raw,total,replies):corpus.append(('accept',raw,str(total),replies))
    def reject(raw):corpus.append(('reject',raw,'unused',0))
    try:
        accept(broker.publish(None,None),0,0)
        accept(broker.unavailable(None),'unknown',0)
        accept(broker.publish(cid,session),0,0)
        final(store,chat,'猫 café 🌲\nline=still plain message text')
        good=broker.publish(cid,session);accept(good,1,1)
        original=next(line[6:] for line in good.decode().splitlines() if line.startswith('reply='))
        parts=original.split('|')
        for key,value in [('protocol','2'),('epoch','AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA'),('frame','wrong'),('unread_total','-1'),('unread_total','01'),('unread_total','NaN'),('unread_total','10001'),('unread_total','2'),('counts','unavailable'),('chat_counts_complete','1')]:reject(replace_field(good,key,value))
        reject(b'\n'.join(line for line in good.split(b'\n') if not line.startswith(b'frame=')))
        reject(good+b'protocol=3\n');reject(good+b'debug=forbidden\n')
        reject(good+('chat_unread='+cid+'|1\n').encode())
        reject(good+b'reply='+original.encode()+b'\n')
        reject(replace_field(good,'reply','|'.join(['2',*parts[1:]])))
        reject(replace_field(good,'reply','|'.join(['01',*parts[1:]])))
        reject(replace_field(good,'reply','|'.join([*parts[:3],'bad-session',parts[4]])))
        reject(replace_field(good,'reply','|'.join([*parts[:4],'not-a-fingerprint'])))
        reject(replace_field(good,'line','%%%'))
        reject(replace_field(good,'line','YQ'))
        reject(replace_field(good,'line',base64.b64encode(b'\xff\xff').decode()))
        reject(good[:-1]);reject(good.replace(b'\n',b'\r\n'));reject(good[:-1]+b'\xff\n')
        reject(good+b'x'*240000)
        reject(good+b'line=YQ==\n'*102)
        reject(b'\n'.join(line for line in good.split(b'\n') if not line.startswith(b'runtime=')))
        store.attach(cid,str(uuid4()),explicit=False);new_session=store.chat(cid)['attached_session']
        final(store,store.chat(cid),'New runtime answer');roundtrip=broker.publish(cid,new_session);accept(roundtrip,2,2)
        for i in range(148):final(store,store.chat(cid),str(i))
        capped=broker.publish(cid,new_session);reply_count=sum(line.startswith(b'reply=') for line in capped.splitlines());assert reply_count==50
        accept(capped,150,reply_count)
        broker.WIRE_CAP=900
        final(store,store.chat(cid),'Long reply '*2000)
        omitted=broker.publish(cid,new_session);assert b'omitted=true\n' in omitted and b'reply=' not in omitted
        accept(omitted,151,0)
        broker.WIRE_CAP=240000
        # Java acknowledges an earlier-session message in a currently loaded-runtime frame.
        manifest=tmp_path/'corpus.txt';lines=[]
        for index,(kind,raw,total,count) in enumerate(corpus):
            path=tmp_path/(str(index)+'.wire');path.write_bytes(raw)
            lines.append(f'{kind} {path} {total} {count}')
        manifest.write_text('\n'.join(lines)+'\n');classes=tmp_path/'classes';classes.mkdir()
        compiler=['java']
        if os.environ.get('SYX_JAVA_HOME'):compiler+=['-Djava.home='+os.environ['SYX_JAVA_HOME']]
        sources=list((ROOT/'dev/java/syx/assistant/candidate').glob('*.java'))
        subprocess.run([*compiler,'-m','jdk.compiler/com.sun.tools.javac.Main','--release','16','-encoding','UTF-8','-d',str(classes),*map(str,sources)],check=True,capture_output=True,text=True)
        good_path=tmp_path/'issued.wire';good_path.write_bytes(roundtrip);receipt_path=tmp_path/'java-receipt.wire'
        checked=subprocess.run(['java','-cp',str(classes),'syx.assistant.candidate.DisplayFrameTest',str(manifest),str(good_path),str(receipt_path)],check=True,capture_output=True,text=True)
        assert f'accepted=7 rejected={len(corpus)-7}' in checked.stdout
        coverage=subprocess.run(['java','-cp',str(classes),'syx.assistant.candidate.DisplayCoverageTest',str(good_path)],check=True,capture_output=True,text=True)
        assert 'coverage policy passed' in coverage.stdout
        applied=broker.acknowledge(receipt_path.read_bytes(),presence=dict(session_id=new_session,fresh=True,live=True))
        assert applied['newly_read']==1
        assert len(broker.history.unread(cid))==150
    finally:store.close()
