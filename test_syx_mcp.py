import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import ValidationError

from syx_mcp import Advisor, Snapshot, Source

ROOT = Path(__file__).parent

@pytest.fixture
def setup(tmp_path):
    state = json.loads((ROOT / 'snapshot.example.json').read_text())
    state['captured_at'] = datetime.now(timezone.utc).isoformat()
    snapshot = tmp_path / 'snapshot.json'
    snapshot.write_text(json.dumps(state))
    return Advisor(snapshot, tmp_path / 'corpus.json'), state


def save(advisor, state):
    advisor.snapshot_path.write_text(json.dumps(state))


def test_missing_game(tmp_path):
    assert Advisor(tmp_path / 'missing', tmp_path / 'corpus').status()['available'] is False


def test_demo_never_live(setup):
    a, _ = setup
    assert a.status()['live'] is False
    result = a.query('resources', '/stockpiles')
    assert result['state']['demo'] is True
    assert result['data'][0]['amount'] == 123


def test_live_freshness_and_unload(setup):
    a, s = setup
    s['demo'] = False
    save(a, s)
    assert a.status()['live'] is True
    s['captured_at'] = (datetime.now(timezone.utc) - timedelta(seconds=90)).isoformat()
    save(a, s)
    assert a.status()['live'] is False
    with pytest.raises(ValueError, match='fresh'):
        a.query('resources')
    s['captured_at'] = datetime.now(timezone.utc).isoformat()
    s['game_loaded'] = False
    save(a, s)
    with pytest.raises(ValueError, match='loaded'):
        a.query('resources')


def test_future_clock_is_not_live(setup):
    a, s = setup
    s['demo'] = False
    s['captured_at'] = (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat()
    save(a, s)
    assert a.status()['live'] is False


def test_session_consistency_and_unavailable(setup):
    a, _ = setup
    with pytest.raises(ValueError, match='changed'):
        a.query('resources', expected_snapshot_id='other-session')
    with pytest.raises(ValueError, match='unavailable'):
        a.query('military')


def test_pagination_and_escaped_pointer(setup):
    a, s = setup
    s['domains']['resources']['data'] = {'a/b': {'~x': list(range(120))}}
    save(a, s)
    result = a.query('resources', '/a~1b/~0x', offset=50, limit=50)
    assert result['data'] == list(range(50, 100))
    assert result['next_offset'] == 100
    assert a.query('resources', '/a~1b/~0x', 100, 50)['next_offset'] is None
    with pytest.raises(ValueError):
        a.query('../auth.json')
    with pytest.raises(ValueError):
        a.query('resources', limit=101)


def test_coverage_validation_and_corruption(setup):
    a, s = setup
    del s['domains']['military']
    with pytest.raises(ValidationError):
        Snapshot.model_validate(s)
    a.snapshot_path.write_text('{')
    assert a.status()['available'] is False


def test_bounded_result(setup):
    a, s = setup
    s['domains']['resources']['data'] = {'large': 'a' * 65537}
    save(a, s)
    with pytest.raises(ValueError, match='large'):
        a.query('resources')


def test_corpus_citations_and_version(setup):
    a, _ = setup
    assert a.search('food')['results'] == []
    # Test-only invented evidence, never shipped as a gameplay guide.
    record = {'id': 'test-1', 'title': 'Test fixture', 'url': 'https://example.com/test-only',
              'kind': 'guide', 'retrieved_at': datetime.now(timezone.utc).isoformat(),
              'game_versions': ['TEST-A'], 'text': 'Food fixture text; not a game fact.'}
    a.corpus_path.write_text(json.dumps([record]))
    result = a.search('food', 'TEST-B')['results'][0]
    assert result['version_compatibility'] == 'mismatch'
    assert result['url'] == record['url']
    record['url'] = 'file:///etc/passwd'
    with pytest.raises(ValidationError):
        Source.model_validate(record)


def test_mcp_transport(setup):
    a, _ = setup
    async def exercise():
        params = StdioServerParameters(command=sys.executable,
            args=['-m', 'syx_mcp'], cwd=str(ROOT),
            env={**os.environ, 'SYX_STATE_DIR': str(a.snapshot_path.parent)})
        async with stdio_client(params) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                listing = await session.list_tools()
                assert {t.name for t in listing.tools} == {
                    'game_status', 'query_game_state', 'search_guidance'}
                assert all(t.annotations.read_only_hint for t in listing.tools)
                result = await session.call_tool('game_status', {})
                assert not result.is_error
                assert 'demo-session' in str(result)
                query = await session.call_tool('query_game_state', {
                    'domain': 'resources', 'pointer': '/stockpiles'})
                assert not query.is_error
                invalid = await session.call_tool('query_game_state', {'domain': '../secret'})
                assert invalid.is_error
    asyncio.run(exercise())
