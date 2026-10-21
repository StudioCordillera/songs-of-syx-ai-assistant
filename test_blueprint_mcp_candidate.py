"""Actual developer MCP discovery/retrieval and schema/wire bounds; no game/provider calls."""
import asyncio,json,os,sys,tempfile
from pathlib import Path
import pytest
from dev.blueprint_examples import load_registry
from dev.blueprint_mcp_candidate import SearchRequest,GetRequest,encoded,isolated_state_dir
ROOT=Path(__file__).resolve().parent

@pytest.mark.parametrize('payload',[{'query':'warehouse','game_version':'0.71.44','execute':True},
 {'query':'warehouse','game_version':'0.71.44','limit':True},
 {'query':'warehouse','game_version':'0.71.44','limit':'1'},
 {'query':'a'*301,'game_version':'0.71.44'},
 {'query':'warehouse','game_version':'current'}])
def test_search_schema_refuses_unknown_coerced_and_oversized_arguments(payload):
    with pytest.raises(ValueError):SearchRequest.model_validate(payload)

@pytest.mark.parametrize('payload',[{'example_id':'../../etc/passwd','game_version':'0.71.44'},
 {'example_id':'warehouse','game_version':'0.71.44','placement':{'x':1}},
 {'example_id':'warehouse'}])
def test_get_schema_refuses_path_action_and_missing_version(payload):
    with pytest.raises(ValueError):GetRequest.model_validate(payload)

def test_actual_json_utf8_budget_preserves_unicode_and_refuses_overflow():
    assert json.loads(encoded({'text':'é😀'}))=={'text':'é😀'}
    assert len(encoded({'text':'😀'*16000}).encode())<65536
    with pytest.raises(ValueError):encoded({'text':'😀'*17000})
    with pytest.raises(ValueError):encoded({'bad':float('nan')})

def test_cli_requires_explicit_isolated_state_and_rejects_links(tmp_path):
    for value in [None,str(tmp_path),str(ROOT/'runtime'),str(Path.home())]:
        with pytest.raises(ValueError):isolated_state_dir(value)
    with tempfile.TemporaryDirectory(dir=ROOT/'runtime',prefix='blueprint-mcp-isolation-') as name:
        p=Path(name);assert isolated_state_dir(name)==p.resolve()
        (p/'real').mkdir();(p/'link').symlink_to(p/'real',target_is_directory=True)
        with pytest.raises(ValueError):isolated_state_dir(str(p/'link'))

def test_actual_stdio_tools_are_read_only_selective_qualified_and_bounded():
    asyncio.run(check_stdio())

async def check_stdio():
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    with tempfile.TemporaryDirectory(dir=ROOT/'runtime',prefix='blueprint-mcp-check-') as name:
        state=Path(name)
        # No snapshot is supplied: these two tools must not invent live-state/UI evidence.
        params=StdioServerParameters(command=sys.executable,args=['-m','dev.blueprint_mcp_candidate'],cwd=str(ROOT),env={'SYX_STATE_DIR':str(state)})
        async with stdio_client(params) as streams:
          async with ClientSession(*streams) as session:
            await session.initialize();listed=await session.list_tools();tools={t.name:t for t in listed.tools}
            assert len(tools)==21
            from syx_mcp import Advisor,create_server
            baseline=await create_server(Advisor(state/'snapshot.json',state/'corpus.json')).list_tools()
            base={t.name:t for t in baseline}
            assert len(base)==19 and set(tools)-set(base)=={'search_blueprint_examples','get_blueprint_example'}
            for name,tool in base.items():assert tools[name].model_dump()==tool.model_dump(),name
            for n in ['search_blueprint_examples','get_blueprint_example']:
                a=tools[n].annotations
                assert a.read_only_hint is True and a.destructive_hint is False and a.open_world_hint is False
                assert tools[n].input_schema['$defs'][('SearchRequest' if n.startswith('search') else 'GetRequest')]['additionalProperties'] is False
            async def call(name,request,error=False):
                result=await session.call_tool(name,{'request':request})
                assert result.is_error==error,result
                assert len(result.content)==1 and result.content[0].type=='text'
                text=result.content[0].text;assert len(text.encode())<=65536
                return text if error else json.loads(text)
            version='0.71.44'
            hits=await call('search_blueprint_examples',{'query':'warehouse aisle','game_version':version})
            assert hits['scope']=='developer_reference_catalog_no_live_state' and len(hits['results'])==1
            assert hits['catalog_reviewed_game_version']=='0.71.44'
            assert 'geometry' not in hits['results'][0] and hits['results'][0]['geometry_included'] is False
            item=await call('get_blueprint_example',{'example_id':hits['results'][0]['id'],'game_version':version})
            assert item['geometry']['grid']==['.....','.RF..','E....','.RF..','.....']
            assert item['example']['source_url'].endswith('/BLUEPRINT_EXAMPLES_CANDIDATE.md')
            assert item['construction_validated'] is item['execution_supported'] is False
            assert item['evidence']['catalog_report_sha256']==load_registry().report_hash
            assert 'state' not in item and 'ui_context' not in item
            other=await call('get_blueprint_example',{'example_id':hits['results'][0]['id'],'game_version':'0.72.0'})
            assert other['compatibility']=='unknown' and other['example']['game_version']==version
            assert (await call('search_blueprint_examples',{'query':'astronomy','game_version':version}))['results']==[]
            assert 'Unknown original schematic' in await call('get_blueprint_example',{'example_id':'missing','game_version':version},True)
            await call('search_blueprint_examples',{'query':'warehouse','game_version':version,'execute':True},True)
            await call('search_blueprint_examples',{'query':'warehouse','game_version':version,'limit':True},True)
            await call('get_blueprint_example',{'example_id':'../../etc/passwd','game_version':version},True)
