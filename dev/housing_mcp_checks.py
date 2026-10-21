"""Fixed retained-original production housing getter/MCP diagnostics checks used by copied native fixtures."""
import json,os,sys,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from run_player_chat_check import native_environment

async def check(state,filename,failed_rooms=0,expected_noble_rows=0):
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    from syx_mcp import Snapshot
    path=state/filename;raw=Snapshot.model_validate_json(path.read_bytes());data=raw.domains['housing'].data['home_records']['data']
    rooms=data['rooms'];assert data['failed_room_reads']==failed_rooms
    noble=[r for r in rooms if r['kind']=='noble_chamber'];assert len(noble)==expected_noble_rows
    if expected_noble_rows:
        assert noble[0]['occupants_reported']==1 and len(noble[0]['occupant_roster']['ids'])==1
    links=[{'room_id':r['room_id'],'resident_id':rid,'roster_index':i} for r in rooms for i,rid in enumerate(r['occupant_roster']['ids'])]
    retained=state/(filename+'.retained');retained.mkdir();shutil.copy2(path,retained/'snapshot.json')
    params=StdioServerParameters(command=sys.executable,args=['-m','syx_mcp'],cwd=str(ROOT),env={**native_environment(os.environ),'SYX_STATE_DIR':str(retained)})
    async with stdio_client(params) as streams:
      async with ClientSession(*streams) as session:
        await session.initialize()
        sources=[{'domain':'housing','path':'/home_records/data/rooms'},{'domain':'housing','path':'/home_assignments/data/rows'}]
        spec={'queries':[{'source':s,'aggregates':{'n':{'op':'count'}}} for s in sources],'expected_snapshot_id':raw.snapshot_id,'include_ui_context':True}
        r=await session.call_tool('select_game_state',{'spec':spec});assert not r.is_error,str(r)
        body=json.loads(next(c.text for c in r.content if c.type=='text'))
        assert [x['rows'] for x in body['results']]==[[{'n':len(rooms)}],[{'n':len(links)}]]
        assert body['state']['snapshot_id']==raw.snapshot_id and body['ui_context']==raw.ui_context
        for result in body['results']:
            diagnostics=result['sources'][0]['collection_diagnostics']
            assert any(d.get('failed_room_reads')==failed_rooms for d in diagnostics)
        r=await session.call_tool('query_game_state',{'domain':'housing','pointer':'/home_assignments/data/rows','limit':100,'expected_snapshot_id':raw.snapshot_id});assert not r.is_error
        result=json.loads(next(c.text for c in r.content if c.type=='text'));assert result['data']==links[:100] and result['total']==len(links)
        if expected_noble_rows:
            query={'source':sources[1],'where':{'eq':[{'field':'/room_id'},noble[0]['room_id']]},'select':{'resident_id':{'field':'/resident_id'}}}
            r=await session.call_tool('select_game_state',{'spec':{'queries':[query],'expected_snapshot_id':raw.snapshot_id}});assert not r.is_error
            result=json.loads(next(c.text for c in r.content if c.type=='text'))
            assert result['results'][0]['rows']==[{'resident_id':noble[0]['occupant_roster']['ids'][0]}]
    return {'home_rows':len(rooms),'relationship_rows':len(links),'noble_rows':len(noble),'failed_room_reads':failed_rooms,
            'actual_mcp_calls':3 if expected_noble_rows else 2,'same_original_snapshot_and_ui':True,'source_failure_diagnostics_preserved':True}
