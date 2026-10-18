"""Check and time bounded selections over a recorded real snapshot, offline.

Never rewrites its timestamp or presents it as current. Excludes game collection,
file parsing, MCP transport and inference. Publishes no player values.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from syx_mcp import Snapshot
from syx_query import QueryEngine


def benchmark(path,repetitions):
    raw=path.read_bytes();snapshot=Snapshot.model_validate_json(raw)
    assert not snapshot.demo and snapshot.game_loaded
    spec=json.loads((ROOT/'selective-query-examples.json').read_text())
    stocks=snapshot.domains['resources'].data['stockpiles']
    flows=snapshot.domains['production'].data['room_data']['flows']
    assert not snapshot.domains['production'].data['room_data']['truncated']
    workforce={r['room_id']:r for r in snapshot.domains['employment'].data['rooms']}
    resources={r['id']:r for r in stocks}
    first=sorted([{'resource':r['id'],'stored':r['stockpile_stored']} for r in stocks if r['stockpile_stored']>0],key=lambda r:r['stored'])
    outputs=[r for r in flows if r['direction']=='output']
    second=sorted([{'room':r['room_id'],'resource':r['resource_id'],'recorded':r['previous_day_units'],
        'employed':workforce[r['room_id']]['employed'],'stored':resources[r['resource_id']]['stockpile_stored']}
        for r in outputs if r['room_id'] in workforce and r['resource_id'] in resources],key=lambda r:r['stored'])
    grouped=defaultdict(list)
    for r in outputs:grouped[r['resource_id']].append(r)
    third=[{'resource':key,'flow_count':len(rows),'recorded_sum':sum(r['previous_day_units'] for r in rows)} for key,rows in sorted(grouped.items())]
    expected=[first[:5],second[:5],third[:20]]
    results=QueryEngine(snapshot).execute(spec)
    assert [r['rows'] for r in results]==expected
    assert [r['matched_total'] for r in results]==[len(first),len(second),len(third)]
    durations=[]
    for _ in range(repetitions):
        began=time.perf_counter();actual=QueryEngine(snapshot).execute(spec);durations.append((time.perf_counter()-began)*1000)
        assert actual==results
    return {'passed':True,'method':'Offline QueryEngine only, on a preserved real snapshot. No game or inference calls.',
        'game_version':snapshot.game_version,'source_snapshot_sha256':hashlib.sha256(raw).hexdigest(),
        'source_observed_at':str(snapshot.captured_at),'query_spec_sha256':hashlib.sha256((ROOT/'selective-query-examples.json').read_bytes()).hexdigest(),
        'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['syx_query.py','syx_mcp.py','dev/benchmark_selective_queries.py']},
        'independent_filter_join_aggregate_parity':True,'query_count':3,'returned_row_counts':[len(r['rows']) for r in results],
        'snapshot_bytes':len(raw),'selected_results_bytes':len(json.dumps(results).encode()),'repetitions':repetitions,
        'local_elapsed_ms':{'median':round(statistics.median(durations),3),'p95':round(sorted(durations)[int(.95*(len(durations)-1))],3),'max':round(max(durations),3)},
        'limits':['One copied city, no large-city latency or collection cost claim. Timings are local descriptive measurements, not a guarantee.',
            'Selected byte count includes query result metadata but excludes outer MCP/status/UI context envelopes; snapshot contains installed references too.',
            'Recorded output sums combine stored buckets with unknown exact age; no calendar alignment, productivity or future throughput claim.',
            'Offline engine timing does not establish live API availability or refresh stale data.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--snapshot',type=Path,required=True)
    p.add_argument('--repetitions',type=int,default=101);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if not 21<=args.repetitions<=500:raise SystemExit('Use 21..500 repetitions')
    report=benchmark(args.snapshot,args.repetitions);args.output.write_text(json.dumps(report,indent=2)+'\n')
    print('Selective filter/join/aggregate parity and offline timing passed.')
