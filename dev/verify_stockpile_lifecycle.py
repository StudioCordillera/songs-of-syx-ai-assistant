"""Actual MCP reads across public, test-only warehouse removal/ID reuse in a copied city."""
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

ROOT=Path(__file__).resolve().parent.parent
FIELDS=['assigned_crates','stored_raw','capacity_raw','reserved_stored_raw','reserved_incoming_raw','reference_id']


async def verify(directory):
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(ROOT),env={**os.environ,'SYX_STATE_DIR':str(directory)})
    checks=[];session_id=None;requests=set();observations=[]
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            for phase in range(3):
                path=directory/f'stockpile-lifecycle-{phase}.json';began=time.monotonic()
                while not path.is_file():
                    if (directory/'stockpile-lifecycle-failure.json').exists():raise AssertionError('Native lifecycle fixture failed')
                    if time.monotonic()-began>100:raise AssertionError('Timed out waiting for lifecycle phase')
                    await asyncio.sleep(.1)
                fixture=json.loads(path.read_text());observations.append(fixture)
                spec={'resource_ids':fixture['resource_ids'],'fields':FIELDS,'limit':100}
                async def call(extra=None,failed=False):
                    result=await session.call_tool('query_live_stockpiles',{'spec':{**spec,**(extra or {})}})
                    assert bool(result.is_error)==failed,str(result)
                    if failed:return str(result)
                    body=json.loads(next(c.text for c in result.content if c.type=='text'))
                    assert body['data']['cell_errors']==0 and body['request_id'] not in requests
                    requests.add(body['request_id']);assert body['session_id']==session_id
                    return body
                if session_id is None:
                    # Read connection identity independently of warehouse fixture metadata.
                    from syx_mcp import Advisor
                    session_id=Advisor(directory/'snapshot.json',directory/'corpus.json').snapshot().session_id
                body=await call();data=body['data']
                assert data['rows']==fixture['rows'] and data['room_count_total']==fixture['warehouse_count']
                assert data['scanned_cells']==len(fixture['rows']) and data['next_cursor'] is None
                if phase<2:
                    assert (await call({'room_ids':[fixture['original_room_id']]}))['data']['rows']==fixture['rows']
                    active=phase==0
                    assert all(r['room_active']==active for r in fixture['rows'])
                    assert (await call({'active':active}))['data']['rows']==fixture['rows']
                    assert (await call({'active':not active}))['data']['rows']==[]
                    if phase==1:
                        assert observations[0]['original_room_id']==fixture['original_room_id']
                        assert observations[0]['rows']!=fixture['rows']
                        for before,after in zip(observations[0]['rows'],fixture['rows']):
                            assert all(before[k]==after[k] for k in ['room_id','room_blueprint_id','anchor_tile_x','anchor_tile_y','resource_id'])
                else:
                    assert data['rows']==[] and data['scanned_cells']==0
                    assert 'Requested room is not a current warehouse' in await call({'room_ids':[fixture['original_room_id']]},failed=True)
                    # A cursor from the old nonempty matrix cannot be continued as if rows persisted.
                    assert 'Cursor exceeds current requested matrix' in await call({'cursor':1},failed=True)
                checks.append({'phase':phase,'rows_checked':len(fixture['rows']),'warehouse_count':fixture['warehouse_count'],
                    'same_session':True,'direct_public_getter_parity':True,'tick':body['tick']})
                (directory/f'stockpile-lifecycle-{phase}.done').write_text('verified\n')
    assert len({c['tick'] for c in checks})==3
    names=['mod/tests/StockpileLifecycleScenario.java','mod/tests/LiveSmoke.java','dev/verify_stockpile_lifecycle.py','dev/run_read_fixture.py']
    report={'passed':True,'evaluated_at':datetime.now(timezone.utc).isoformat(),'checks':checks,
        'successful_mcp_pages':len(requests),'actual_distinct_instance_same_id_reuse':True,
        'removed_explicit_id_and_old_cursor_refused':True,'inference_calls':0,
        'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},
        'limits':['One paused copied city and one actual warehouse slot, not multi-room ordering, hard caps, faults or large-city performance.',
            'Fixed test-only public remove/create/deactivate/clear mutations; no production gameplay command or normal-profile change.',
            'Baseline includes one allocator-normalizing reconstruction because a loaded save can have earlier free slots; then the measured reconstruction actually reuses the baseline ID.',
            'Reconstruction reuses geometry and furnishing; zero-default construction resource costs and copied statistics are fixture inputs, not a normal build/material simulation.',
            'Crate disposal/construction may scatter or collect copied-city goods; in-memory state is discarded, never saved or claimed restored.',
            'Direct getter baselines share engine storage. Same room ID, blueprint, anchor and session can refer to a distinct instance; metadata is not durable identity.',
            'Existing published player JAR and ZIP remain unchanged; this report adds lifecycle coverage only.']}
    (directory/'stockpile-lifecycle-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True)
    asyncio.run(verify(p.parse_args().state_dir))
