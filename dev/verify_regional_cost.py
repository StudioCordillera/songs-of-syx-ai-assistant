"""Descriptive native regional collector/encoding and actual sequential MCP latency samples."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def distribution(values):
    if not values or any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in values):
        raise ValueError('Expected finite nonnegative timing samples')
    ordered = sorted(values)
    return {'count': len(values), 'min': ordered[0], 'median': statistics.median(values),
            'p95': ordered[math.ceil(.95 * len(values)) - 1], 'max': ordered[-1]}


async def verify(directory):
    root = Path(__file__).resolve().parent.parent
    directory = directory.resolve()
    began = time.monotonic()
    while time.monotonic() - began < 120:
        try:
            fixture = json.loads((directory / 'regional-cost-fixture.json').read_text())
            break
        except (FileNotFoundError, json.JSONDecodeError):
            await asyncio.sleep(.2)
    else:
        raise AssertionError('No native regional cost samples')
    names = ['single_cell', 'full_row_page', 'empty_amount_scan_cap', 'empty_faction_scan_cap']
    assert len(fixture['samples']) == 128 and fixture['all_sample_getter_parity'] is True
    native = {}
    for name in names:
        samples = [s for s in fixture['samples'] if s['case'] == name]
        assert [s['sample'] for s in samples] == list(range(32))
        assert all(s['returned_rows'] == (1 if name == names[0] else 100 if name == names[1] else 0)
                   and s['scanned_cells'] == (1 if name == names[0] else 100 if name == names[1] else 4096)
                   and 0 < s['response_bytes'] <= 65536 for s in samples)
        native[name] = {'first_sample': samples[0], 'warm_collector_ms': distribution([s['collector_ns'] / 1e6 for s in samples[1:]]),
                        'warm_encoding_utf8_ms': distribution([s['encoding_utf8_ns'] / 1e6 for s in samples[1:]]),
                        'max_response_bytes': max(s['response_bytes'] for s in samples)}
    fields = ['accrued_output_raw', 'days_until_configured_output', 'reference_id', 'faction_id']
    base = {'region_ids': fixture['region_ids'], 'resource_ids': fixture['resource_ids'], 'fields': fields, 'limit': 100}
    specs = {names[0]: {**base, 'region_ids': base['region_ids'][:1], 'resource_ids': base['resource_ids'][:1]},
             names[1]: base, names[2]: {**base, 'min_accrued_output': 2147483647},
             names[3]: {**base, 'faction_id': 2147483647}}
    parameters = StdioServerParameters(command=sys.executable, args=['-m', 'syx_mcp'], cwd=str(root),
                                      env={**os.environ, 'SYX_STATE_DIR': str(directory)})
    mcp_samples = {name: [] for name in names}
    async with stdio_client(parameters) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            for repeat in range(11):
                for name, spec in specs.items():
                    started = time.perf_counter_ns()
                    result = await session.call_tool('query_live_regional_outputs', {'spec': spec})
                    elapsed = time.perf_counter_ns() - started
                    assert not result.is_error, str(result)
                    body = json.loads(next(c.text for c in result.content if c.type == 'text'))
                    data = body['data']
                    expected = fixture['expected_page_rows'][:1 if name == names[0] else 100] if name in names[:2] else []
                    assert data['rows'] == expected and data['cell_errors'] == 0
                    assert data['scanned_cells'] == (1 if name == names[0] else 100 if name == names[1] else 4096)
                    assert data['next_cursor'] == (None if name == names[0] else 100 if name == names[1] else 4096)
                    assert body['observer_phase'] == 'GAME.addAfterUpdate' and body['read_mode'] == 'regional_page'
                    assert body['ui_context']['active_view'] == body['scene']['active_view']
                    captured = datetime.fromisoformat(body['captured_at'].replace('Z', '+00:00'))
                    assert 0 <= (datetime.now(timezone.utc) - captured).total_seconds() < 8
                    mcp_samples[name].append(elapsed / 1e6)
    report = {'passed': True, 'active_regions': fixture['active_regions'], 'loaded_resources': fixture['loaded_resources'],
              'requested_regions': len(base['region_ids']), 'requested_resources': len(base['resource_ids']),
              'native_samples': fixture['samples'], 'native_summary': native,
              'mcp_sequential_samples_ms': mcp_samples,
              'mcp_sequential_warm_ms': {name: distribution(values[1:]) for name, values in mcp_samples.items()},
              'all_sample_getter_parity': True, 'mcp_calls_checked': 44, 'java_version': fixture['java_version'],
              'limits': ['Finite paused copied city/campaign, 100 requested regions and all loaded resources; not a largest-world/city or all-projection benchmark.',
                         '32 interleaved native samples per case at >=250ms spacing; first excluded from 31-sample warm summaries, not a cold JVM/filesystem claim.',
                         'Collector interval includes production scene/UI DTO collection, excludes parser, parity checks, encoding, disk/IPC, regular collector and model. Separate encoding is run by this fixture on update thread; production encoding is off-thread.',
                         '44 sequential actual stdio MCP calls, first of 11 per case excluded from warm summary. Latency includes helper validation, shared mailbox lock/polling, update scheduling, game worker serialization/file IPC and stdio. No model, concurrent-load, FPS or acceptance threshold claim.',
                         'Native getter parity checks every sample; MCP checks exact independently read paused-game rows. No counter/ownership writes, retained capture, cap/fault injection or natural rollover proof.']}
    (directory / 'regional-cost-validation.json').write_text(json.dumps(report, indent=2) + '\n')
    (directory / 'verifier.done').write_text('Regional cost/parity checks passed\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', type=Path, required=True)
    asyncio.run(verify(parser.parse_args().state_dir))
