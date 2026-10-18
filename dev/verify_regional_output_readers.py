"""Validate private candidate-reader metadata and current MCP identity joins; no new counter tool."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import time
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from syx_mcp import Advisor
from profile_collection_cost import distribution


async def verify(directory):
    directory=directory.resolve();root=Path(__file__).resolve().parent.parent;start=time.monotonic()
    while time.monotonic()-start<120:
        if (directory/'regional-output-reader-fixture.json').exists():break
        await asyncio.sleep(.2)
    else:raise AssertionError('No native regional output candidate result')
    fixture=json.loads((directory/'regional-output-reader-fixture.json').read_text());assert fixture['passed']
    shape=fixture['shape'];assert shape['counter_cells']==shape['regions']*shape['resources']<=10000
    assert shape['counter_cells']==shape['natural_positive_cells']+shape['natural_zero_cells'] and shape['negative_cells']==0
    assert fixture['configured_day_offset_checks']==shape['resources']
    assert fixture['controlled_values']==[0,37,2147483647]
    assert all(fixture[k] for k in ['unrelated_cells_unchanged_during_controls','controlled_counter_restored','repeated_matrix_unchanged'])
    samples=fixture['samples'];assert len(samples)==32 and all(s['cells']==shape['counter_cells'] for s in samples)
    advisor=Advisor(directory/'snapshot.json',directory/'corpus.json');snapshot=advisor.snapshot();assert advisor.status(snapshot)['live']
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(root),env={**os.environ,'SYX_STATE_DIR':str(directory)})
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            for domain,path,expected in [('world','/regions',set(fixture['region_ids'])),('resources','/stockpiles',set(fixture['resource_ids']))]:
                result=await session.call_tool('select_game_state',{'spec':{'queries':[{'source':{'domain':domain,'path':path},
                    'select':{'id':{'field':'/id'}},'limit':100}]}})
                assert not result.is_error,str(result)
                observed=json.loads(next(c.text for c in result.content if c.type=='text'))['results'][0]
                assert observed['matched_total']==len(expected)
                assert all(row['id'] in expected for row in observed['rows'])
                # Independent complete identity comparison uses the same local exported DTO,
                # not a substitute for the separate production counter MCP verifier.
                assert {row['id'] for row in snapshot.domains[domain].data[path[1:]]}==expected
    report={'passed':True,'stage':'Native reader-only probe; production counter MCP parity is validated separately',
        'shape':shape,'configured_day_offset_checks':fixture['configured_day_offset_checks'],
        'controlled_values':fixture['controlled_values'],'unrelated_cells_unchanged_during_controls':True,
        'controlled_counter_restored':True,'repeated_matrix_unchanged':True,'matrix_sha256':fixture['matrix_sha256'],
        'samples':samples,'read_and_int_array_ms':distribution([s['read_and_int_array_ns']/1e6 for s in samples]),
        'current_mcp_region_resource_identity_parity':True,'limits':fixture['limits']+[
            'Native shape/results alone do not implement a DTO, field definition, selective counter route or unavailable-scene diagnostics.',
            'All 32 timing samples follow initial reads/control checks; none is a cold-start measurement.']}
    (directory/'regional-output-reader-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (directory/'verifier.done').write_text('verified\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True)
    asyncio.run(verify(p.parse_args().state_dir))
