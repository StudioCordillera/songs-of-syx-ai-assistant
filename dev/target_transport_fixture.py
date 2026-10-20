"""Test-only production MCP server with synthetic capture readers; never a player.

Run only against disposable test snapshots. No game process, secrets or native game automation.
"""
from copy import deepcopy
from pathlib import Path
import argparse
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from syx_mcp import Advisor, create_server
import syx_capture
import syx_tiles
import syx_regions


def serve(snapshot):
    advisor = Advisor(snapshot, snapshot.parent / 'empty-test-corpus.json')

    def payload(kind):
        state = advisor.status()
        result = {k: state[k] for k in ('session_id', 'game_version', 'captured_at', 'tick', 'scene')}
        result.update(request_id=str(uuid4()), observer_phase='synthetic_only',
                      scope='synthetic_transport_fixture', consistency='synthetic detached rows only',
                      ui_context={'active_view': state['scene']['active_view']})
        rows = [{'id': i, 'tile_x': i, 'tile_y': 0} for i in range(3)]
        result['data'] = {'rows': rows, 'next_cursor': None, 'scanned_slots': 3, 'predicate_errors': 0}
        if kind == 'tile':
            result['data'].update(bounds=[0, 0, 3, 1], scanned_tiles=3)
            for row in rows: row['room'] = {'available': False, 'data': None, 'reason': 'synthetic_unknown'}
        if kind == 'regional_output':
            result['data'].update(scanned_cells=3, cell_errors=0)
            result['data']['rows'] = [{'region_id': i, 'resource_id': 'grain', 'accrued_output_raw': i} for i in range(3)]
        return deepcopy(result)

    syx_capture.capture_entities = lambda *a: payload('entity')
    syx_tiles.query_tiles = lambda *a: payload('tile')
    syx_regions.query_regional_outputs = lambda *a, **k: payload('regional_output')
    create_server(advisor).run()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    serve(parser.parse_args().snapshot)
