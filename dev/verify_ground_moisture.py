"""Validate a private candidate-reader fixture and existing tile geometry through actual MCP.

Moisture is not yet an MCP field. Public coordinate/linear reader parity is native;
MCP calls here verify only the unchanged public terrain route at four sampled corners.
"""
import argparse,asyncio,hashlib,json,math,os,statistics,sys,time
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from syx_mcp import Advisor

async def verify(directory):
    directory=directory.resolve();advisor=Advisor(directory/'snapshot.json',directory/'corpus.json');started=time.monotonic()
    while time.monotonic()-started<180:
        try:
            fixture=json.loads((directory/'ground-moisture-fixture.json').read_text());snapshot=advisor.snapshot()
            if advisor.status(snapshot)['live'] and snapshot.scene['active_view']=='settlement':break
        except (FileNotFoundError,json.JSONDecodeError,TypeError):pass
        await asyncio.sleep(.2)
    else:raise RuntimeError('No fresh completed candidate ground-moisture fixture')
    assert fixture['passed'] and fixture['scene']['active_view']=='settlement'
    points=fixture['sample_points'];assert len(points)==4096
    assert len({tuple(p[:2]) for p in points})==4096
    w,h=fixture['width'],fixture['height'];assert w>=64 and h>=64
    for i,(x,y,b,c) in enumerate(points):
        assert (x,y)==((i%64)*(w-1)//63,(i//64)*(h-1)//63)
        assert all(type(v) in (int,float) and math.isfinite(v) and 0<=v<=1 and abs(v*15-round(v*15))<1e-10 for v in (b,c))
    samples=fixture['samples'];assert len(samples)==64
    for i,s in enumerate(samples):
        assert s['sample']==i and s['tile_count']==4096 and s['public_getter_calls_in_timed_loop']==8192
        assert s['coordinate_linear_comparisons']==8192 and type(s['reader_loop_ns']) is int and s['reader_loop_ns']>0
        assert all(0<=s[k]<=4096 for k in ['different_base_current_tiles','changed_from_first_tiles'])
    assert fixture['out_of_bounds_zero_points']==[[-1,0],[0,-1],[w,0],[0,h]]
    root=Path(__file__).resolve().parent.parent
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(root),env={**os.environ,'SYX_STATE_DIR':str(directory)})
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            for p in fixture['anchors']:
                x,y=p['tile_x'],p['tile_y']
                r=await session.call_tool('query_live_tiles',{'spec':{'tile_bounds':[x,y,x+1,y+1],'fields':['terrain'],'limit':1,'expected_session_id':snapshot.session_id}})
                assert not r.is_error,str(r)
                d=json.loads(next(c.text for c in r.content if c.type=='text'))
                assert d['session_id']==snapshot.session_id and d['scene']['active_view']=='settlement'
                assert d['data']['scanned_tiles']==1 and d['data']['predicate_errors']==0 and d['data']['next_cursor'] is None
                row=d['data']['rows'][0];assert (row['tile_x'],row['tile_y'])==(x,y) and row['terrain']['available'] and row['terrain']['data']['key']==p['terrain_id']
    warm=sorted(s['reader_loop_ns']/1e6 for s in samples[1:])
    report={'passed':True,'stage':'Developer candidate public-reader validation, not production MCP moisture support',
        'checks':{'distinct_sampled_coordinates':4096,'native_samples':64,'coordinate_linear_comparisons':64*8192,
            'public_reader_range_and_1_over_15_quantization':True,'out_of_bounds_zero_defaults':4,
            'unchanged_mcp_terrain_anchor_calls':4,'moisture_mcp_calls':0,
            'first_sample_different_base_current_tiles':samples[0]['different_base_current_tiles'],
            'first_sample_distinct_base_values':samples[0]['distinct_base_values'],'first_sample_distinct_current_values':samples[0]['distinct_current_values'],
            'last_sample_changed_from_first_tiles':samples[-1]['changed_from_first_tiles'],
            'first_sample_base_min':samples[0]['base_min'],'first_sample_base_max':samples[0]['base_max'],
            'first_sample_current_min':samples[0]['current_min'],'first_sample_current_max':samples[0]['current_max']},
        'map_shape':{'width':w,'height':h,'sampling':'64x64 uniformly spaced grid spanning four map edges; not every tile'},
        'reader_loop_cost_ms':{'first_sample':samples[0]['reader_loop_ns']/1e6,'warm_count':63,'min':min(warm),'median':statistics.median(warm),'p95':warm[int(.95*(len(warm)-1))],'max':max(warm)},
        'timing_scope':'Two coordinate getters per sampled tile plus loop and preallocated array stores. Coordinate/linear comparisons and metadata/JSON construction excluded; no full collector, request, encoding, MCP, model, FPS or cold-JVM claim.',
        'raw_private_fixture_sha256':hashlib.sha256((directory/'ground-moisture-fixture.json').read_bytes()).hexdigest(),
        'inference_calls':0,'limits':['Paused finite copied city only; no moisture writes, weather/irrigation controls, natural evolution, cap/fault injection, larger-map cost or all-scene acceptance.',
            'Native comparisons use public coordinate and linear overloads sharing the same stored implementation, not independent private raw storage or a second ground-truth sensor.',
            'Only base/current stored readers reviewed; total/environmental water, weather precipitation/growth, fertility/yield/forecasts remain separate and unexposed.',
            'Existing MCP terrain calls verify four coordinate/session anchors, not new moisture fields. Production source/player unchanged.']}
    (directory/'ground-moisture-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (directory/'verifier.done').write_text('done')
    print('Stored-moisture candidate: 4096 coordinates / 64 samples; four existing MCP terrain anchors passed.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state-dir',type=Path,required=True);a=p.parse_args();asyncio.run(verify(a.state_dir))
