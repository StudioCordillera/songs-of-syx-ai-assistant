"""Real multi-warehouse MCP paging, hard scan/row bounds and ordered removal in a copied city."""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from syx_mcp import Advisor

ROOT=Path(__file__).resolve().parent.parent
FIELDS=['assigned_crates','stored_raw','capacity_raw','reserved_stored_raw','reserved_incoming_raw','reference_id']


def project(rows,fields):
    excluded=set(FIELDS)-set(fields)
    return [{k:v for k,v in row.items() if k not in excluded} for row in rows]


async def verify(directory):
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(ROOT),env={**os.environ,'SYX_STATE_DIR':str(directory)})
    checks=[];requests=set();max_bytes=0;session_id=None;previous=None
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            for phase in range(2):
                path=directory/f'stockpile-matrix-{phase}.json';began=time.monotonic()
                while not path.is_file():
                    if (directory/'stockpile-matrix-failure.json').exists():raise AssertionError('Native matrix fixture failed')
                    if time.monotonic()-began>100:raise AssertionError('Timed out waiting for matrix phase')
                    await asyncio.sleep(.1)
                fixture=json.loads(path.read_text());expected=fixture['rows'];keys=fixture['resource_ids'];ids=fixture['room_ids']
                assert len(ids)==101-phase and len(keys)==42 and len(expected)==len(ids)*42
                if session_id is None:session_id=Advisor(directory/'snapshot.json',directory/'corpus.json').snapshot().session_id
                if previous is not None:
                    assert ids==previous['room_ids'][:1]+previous['room_ids'][2:]
                    prior_rows=[r for r in previous['rows'] if r['room_id']!=fixture['removed_room_id']]
                    assert expected==[{**r,'matrix_position':i} for i,r in enumerate(prior_rows)]
                base={'resource_ids':keys,'fields':FIELDS,'limit':70}
                async def call(extra=None,failed=False):
                    nonlocal max_bytes
                    result=await session.call_tool('query_live_stockpiles',{'spec':{**base,**(extra or {})}})
                    assert bool(result.is_error)==failed,str(result)
                    if failed:return str(result)
                    text=next(c.text for c in result.content if c.type=='text');max_bytes=max(max_bytes,len(text.encode()))
                    assert max_bytes<=65536
                    body=json.loads(text);assert body['session_id']==session_id and body['request_id'] not in requests
                    requests.add(body['request_id']);data=body['data']
                    assert data['cell_errors']==0 and data['room_count_total']==(len(extra['room_ids']) if extra and extra.get('room_ids') else len(ids))
                    assert body['observer_phase']=='GAME.addAfterUpdate'
                    return data
                cursor=0;rows=[];pages=0
                while True:
                    d=await call({'cursor':cursor});pages+=1;rows.extend(d['rows'])
                    assert d['scanned_cells']==min(70,len(expected)-cursor)
                    cursor=d['next_cursor']
                    if cursor is None:break
                assert rows==expected
                cap=await call({'fields':['stored_raw'],'limit':100})
                assert cap['rows']==project(expected[:100],['stored_raw'])
                assert cap['scanned_cells']==100 and cap['next_cursor']==100
                empty={'filters':[{'field':'stored_raw','op':'gt','value':2147483647}],'scan_limit':4096,'limit':100}
                scan=await call(empty)
                assert scan['rows']==[] and scan['scanned_cells']==4096 and scan['next_cursor']==4096
                tail=await call({**empty,'cursor':4096})
                assert tail['rows']==[] and tail['scanned_cells']==len(expected)-4096 and tail['next_cursor'] is None
                selected=[ids[-1],ids[0],ids[2]];resource=keys[0]
                explicit=await call({'room_ids':selected,'resource_ids':[resource],'limit':100})
                lookup={(r['room_id'],r['resource_id']):r for r in expected}
                assert explicit['rows']==[{**lookup[(rid,resource)],'matrix_position':i} for i,rid in enumerate(selected)]
                if phase==1:
                    assert 'Requested room is not a current warehouse' in await call({'room_ids':[fixture['removed_room_id']]},failed=True)
                checks.append({'phase':phase,'warehouse_count':len(ids),'matrix_cells_checked':len(expected),'full_projection_pages':pages,
                    'actual_row_limit':100,'actual_empty_scan_limit':4096,'empty_tail_cells':tail['scanned_cells'],'explicit_reordered_rooms_checked':3})
                previous=fixture
                (directory/f'stockpile-matrix-{phase}.done').write_text('verified\n')
    names=['mod/tests/StockpileMatrixScenario.java','mod/tests/LiveSmoke.java','dev/verify_stockpile_matrix.py','dev/run_read_fixture.py']
    report={'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'successful_mcp_pages':len(requests),
        'maximum_observed_tool_text_bytes':max_bytes,'ordered_slot_shift_after_removal':True,'inference_calls':0,
        'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},
        'limits':['100 real small test warehouses are constructed through public APIs in a paused copied city; not a representative populated larger settlement or ordinary build/material simulation.',
            'Construction uses real furnishing, zero-default RoomInit inputs and fixed path/room checks; in-memory effects are discarded without saving, not claimed restored.',
            'All six projected values match public stored getters sharing engine storage; no independent physical inventory or cross-page transaction claim.',
            'Native 4096-cell scan and 100-row limits plus one ordered removal are exercised. Byte overflow, injected registry/cell faults, wider lifecycle and worst-case latency/FPS remain unvalidated.',
            'Source-verified fixed public fixture mutations do not expose production game actions. Published player source and latest/previous ZIPs remain unchanged.']}
    (directory/'stockpile-matrix-validation.json').write_text(json.dumps(report,indent=2)+'\n');return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True)
    asyncio.run(verify(p.parse_args().state_dir))
