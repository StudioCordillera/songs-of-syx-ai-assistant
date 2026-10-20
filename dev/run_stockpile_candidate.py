"""Explicit copied-city native check of an unregistered per-warehouse reader candidate."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / 'dev')]
from run_stockpile_probe import run, sha
from game_fixture_lock import exclusive_fixture

CANDIDATE = ROOT / 'dev/candidates/stockpiles'


async def verify(state, manifest):
    fixture_path = state / 'stockpile-fixture.json'
    if fixture_path.stat().st_size > 65536:
        raise ValueError('Candidate fixture metadata exceeds 64 KiB')
    result = json.loads(fixture_path.read_text())
    assert result['passed'] and result['controlled_room_restored'] and result['controlled_scope_flags_restored']
    names = [c['name'] for c in result['cases']]
    assert len(set(names)) == len(names) == 13 and all(c['passed'] for c in result['cases'])
    assert 0 < result['room_count'] <= 100 and 0 < result['resource_count'] <= 100
    assert result['matrix_cells'] == result['room_count'] * result['resource_count']
    assert result['counter_comparisons'] >= result['matrix_cells'] * 15
    assert 0 < result['maximum_observed_response_bytes'] <= 65536
    times = result.pop('request_parse_collect_encode_ns')
    assert len(times) == 32 and all(type(t) is int and t >= 0 for t in times)
    warm = times[1:]
    return {
        'passed': True, 'checked_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'Detached per-warehouse candidate invoked on the public game after-update thread in one paused copied city. No candidate mailbox, MCP endpoint or player integration.',
        'native_checks': result,
        'timing': {'interval': 'Request frame construction, parsing, collection and detached JSON encoding together; no IPC/MCP/provider.',
                   'warm_samples': len(warm), 'warm_median_ms': statistics.median(warm) / 1e6, 'warm_max_ms': max(warm) / 1e6},
        'production_mod_jar_sha256': manifest['mod_jar_sha256'],
        'candidate_class_packaged_in_player': False,
        'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in [
            CANDIDATE/'StockpileScenario.java', CANDIDATE/'syx/assistant/StockpileReadRequest.java',
            ROOT/'dev/run_stockpile_candidate.py', ROOT/'dev/run_stockpile_probe.py', ROOT/'dev/native_game_completion.py', ROOT/'mod/tests/LiveSmoke.java']},
        'private_fixture_sha256': sha(fixture_path),
        'limits': [
            'The finite copied save has the reported number of warehouses/resources; this is not large-city, 100-room, hard 4096-cell or 100-row cap/fault acceptance.',
            'The independent resource-overload tally getters share underlying storage; parity is not independent physical inventory truth.',
            'Immediate public deactivate/reactivate and two temporarily changed public scope flags are test-only, restored within the callback; no save is written.',
            'Scope-flag refusal is not actual battle/setup lifecycle coverage. Room removal/reuse, absent SETT, malformed registries and per-cell exceptions remain untested.',
            'World-view access observes instantiated city bookkeeping, not selected warehouses or world inventories. No durable ID or exact tally-age guarantee.',
            'No mailbox, Python schema/response validator, MCP parity, cross-page consistency, retained capture, runtime byte-bound refusal or paid player acceptance.',
            'Timings include request construction, parse, collect and encoding together in one callback; not standalone collector cost, scheduling/IPC, concurrent load, FPS or worst-case acceptance.',
        ],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('game-dir', 'jdk-home', 'java', 'save'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--candidate-dir', type=Path)
    parser.add_argument('--validation', type=Path)
    args = parser.parse_args()
    if (ROOT/'mod/src/main/java/syx/assistant/StockpileReadRequest.java').exists():
        parser.error('Historical detached fixture requires checkout 8da6798; current production uses dev/run_read_fixture.py --case stockpile-live. Refusing to shadow the current packaged reader.')
    with exclusive_fixture():
        run(args, scenario_override=CANDIDATE/'StockpileScenario.java',
            extra_sources=[CANDIDATE/'syx/assistant/StockpileReadRequest.java'], verifier=verify,
            report_name='stockpile-candidate-native-validation.json')
