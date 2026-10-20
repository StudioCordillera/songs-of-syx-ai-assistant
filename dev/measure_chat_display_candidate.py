"""Synthetic disposable-history broker timings; no game/provider/normal history access."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time
from uuid import uuid4

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from dev.chat_display_candidate import DisplayBroker
from syx_chat_store import ChatStore


def measure(turns,samples):
    with tempfile.TemporaryDirectory(prefix='syx-display-cost-') as temporary:
        store=ChatStore(Path(temporary));session=str(uuid4());chat=store.new(session,model='deepseek-v4-pro');cid=chat['chat_id']
        broker=DisplayBroker(store);broker.history.initialize()
        try:
            for _ in range(turns):
                tid=str(uuid4());store.begin(cid,tid,session,'Synthetic question')
                store.append(cid,tid,session,'assistant',{'text':'Synthetic final answer.','completed':True});store.finish(cid,tid,'completed')
            start=time.perf_counter_ns();raw=broker.publish(cid,session);first=(time.perf_counter_ns()-start)/1e6
            scans=[];cached=[]
            for _ in range(samples):
                broker._cache_key=None
                start=time.perf_counter_ns();current=broker.publish(cid,session);scans.append((time.perf_counter_ns()-start)/1e6)
                assert current==raw
                start=time.perf_counter_ns();current=broker.publish(cid,session);cached.append((time.perf_counter_ns()-start)/1e6)
                assert current==raw
            def timings(values):return dict(samples=len(values),median_ms=statistics.median(values),max_ms=max(values))
            return dict(completed_turns=turns,synthetic_event_rows=store.db.execute('SELECT count(*) FROM events').fetchone()[0],wire_bytes=len(raw),first_publish_ms=first,
                forced_changed_history_scan=timings(scans),unchanged_refresh=timings(cached),stable_issued_frame=True)
        finally:store.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    results=[measure(turns,31) for turns in [100,10000]]
    paths=['dev/measure_chat_display_candidate.py','dev/chat_display_candidate.py','dev/chat_history_candidate.py','syx_chat_store.py']
    report=dict(passed=True,validated_at=datetime.now(timezone.utc).isoformat(),cases=results,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        game_calls=0,inference_calls=0,limits=['Synthetic one-chat fixed short texts in disposable SQLite, not representative real history/game or end-to-end latency.',
        'First publish is not cold-OS-cache/JVM evidence; scan and unchanged timings describe only this host workload.',
        'History mutation is simulated by forcing cache invalidation; real external-writer behavior has separate offline tests.',
        'No production performance, UI repaint, worst-case byte-limit, concurrent-writer or FPS acceptance.'])
    args.output.write_text(json.dumps(report,indent=2)+'\n');print('Synthetic detached-display timings passed')
