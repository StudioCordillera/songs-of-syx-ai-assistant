"""Production entry-point/schema and embedded source parity; no inference or game."""
import asyncio
import json
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from syx_blueprints import load_registry as production_registry
from dev.blueprint_examples import load_registry as candidate_registry
from syx_blueprint_data import CORPUS_BYTES, CATALOG_REPORT_BYTES
from make_user_test import MODULES

ROOT = Path(__file__).resolve().parent


def test_embedded_artifacts_and_registry_match_reviewed_original_bytes():
    assert CORPUS_BYTES == (ROOT / 'blueprint-examples-candidate.json').read_bytes()
    assert CATALOG_REPORT_BYTES == (ROOT / 'BLUEPRINT_CATALOG_VALIDATION.json').read_bytes()
    actual, expected = production_registry(), candidate_registry()
    for version in ['0.71.44', '0.72.0']:
        assert actual.search('warehouse', version) == expected.search('warehouse', version)
        assert actual.get('warehouse-two-items-teaching-grid', version) == expected.get('warehouse-two-items-teaching-grid', version)
    assert {'syx_blueprints', 'syx_blueprint_data', 'syx_blueprint_tools', 'syx_blueprint_chat'} <= set(MODULES)


def test_default_production_stdio_has_read_only_selective_reference_tools_without_snapshot(tmp_path):
    async def scenario():
        params = StdioServerParameters(command=sys.executable, args=['-m', 'syx_mcp'], cwd=str(ROOT),
            env={'SYX_STATE_DIR': str(tmp_path)})
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                tools = {t.name: t for t in (await session.list_tools()).tools}
                assert len(tools) == 21
                for name in ['search_blueprint_examples', 'get_blueprint_example']:
                    a = tools[name].annotations
                    assert a.read_only_hint and a.idempotent_hint and not a.destructive_hint and not a.open_world_hint
                result = await session.call_tool('search_blueprint_examples', {'request': {'query': 'warehouse', 'game_version': '0.71.44'}})
                assert not result.is_error
                hits = json.loads(result.content[0].text)
                assert hits['scope'] == 'original_reference_catalog_no_live_state'
                assert 'geometry' not in hits['results'][0]
                result = await session.call_tool('get_blueprint_example', {'request': {'example_id': hits['results'][0]['id'], 'game_version': '0.72.0'}})
                assert not result.is_error
                item = json.loads(result.content[0].text)
                assert item['compatibility'] == 'unknown'
                assert item['citation'] == production_registry().citation()
                assert item['execution_supported'] is item['construction_validated'] is False
                assert not (tmp_path / 'snapshot.json').exists()
    asyncio.run(scenario())
