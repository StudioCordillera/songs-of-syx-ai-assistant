"""Compile the detached stockpile candidate and test its wire codec without starting the game."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'dev'))
from verify_bytecode import disassemble, method, fingerprint
from review_stockpile_boundary import stored_reader


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(game, jdk, catalog_path):
    jar = game / 'SongsOfSyx.jar'
    archive = game / 'info/SongsOfSyx-sources.jar'
    if catalog_path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError('Declaration catalog exceeds bound')
    catalog = json.loads(catalog_path.read_text())
    assert catalog['game_jar_sha256'] == sha(jar)
    assert catalog['source_archive_sha256'] == sha(archive)
    required = ['settlement.room.main.RoomsMap#getByIndex(int)', 'settlement.room.main.RoomsMap#max()']
    records = {m['id']: m for m in catalog['members'] if m['id'] in required}
    assert set(records) == set(required)
    java = ['java', '-Djava.home=' + str(jdk.resolve())]
    bytecode = disassemble(java, jar, 'settlement.room.main.RoomsMap')
    signatures = ['public settlement.room.main.Room getByIndex(int);', 'public int max();']
    body = [method(bytecode, s) for s in signatures]
    stored_reader(body[0], ('rooms:', 'aaload', 'areturn'))
    stored_reader(body[1], ('rooms:', 'arraylength', 'ireturn'))
    assert not any(re.search(r'\binvoke\w*\b', code) for code in body)
    management = []
    with zipfile.ZipFile(archive) as z:
        manager = z.read('view/ui/manage/IManager.java')
        full_view = z.read('view/ui/manage/IFullView.java')
        assert b'private IFullView current;' in manager
        assert b'public class IFullView {' in full_view
        declared = sorted(m['id'] for m in catalog['members'] if m['owner'] == 'view.ui.manage.IFullView' and m['kind'] == 'METHOD')
        assert declared == ['view.ui.manage.IFullView#activate()', 'view.ui.manage.IFullView#back()', 'view.ui.manage.IFullView#hoverInfoGet(snake2d.util.gui.GUI_BOX)', 'view.ui.manage.IFullView#init()']
        for name, raw in [('view/ui/manage/IManager.java', manager), ('view/ui/manage/IFullView.java', full_view)]:
            management.append({'source_file': name, 'source_sha256': hashlib.sha256(raw).hexdigest()})
        for record in records.values():
            assert 'public' in record['modifiers']
            assert record['source_match'] == 'unique_signature_anchor'
            source = record['source_candidates'][0]
            assert hashlib.sha256(z.read(source['source_file'])).hexdigest() == source['source_sha256']
    if (ROOT / 'mod/src/main/java/syx/assistant/StockpileReadRequest.java').exists():
        raise ValueError('Historical detached checker requires its pre-production checkout (8da6798); current production uses dev/review_stockpile_live_contract.py and dev/run_read_fixture.py --case stockpile-live')
    production = sorted((ROOT / 'mod/src/main/java').rglob('*.java'))
    candidates = sorted((ROOT / 'dev/candidates/stockpiles/syx/assistant').rglob('*.java'))
    assert len(candidates) == 2 and not any(p.name == 'StockpileReadRequest.java' for p in production)
    with tempfile.TemporaryDirectory(prefix='syx-stockpile-codec-') as temporary:
        classes = Path(temporary) / 'classes'
        classes.mkdir()
        subprocess.run([*java, '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '16', '-encoding', 'UTF-8',
            '-cp', str(jar), '-d', str(classes), *map(str, production + candidates)], check=True, timeout=90, capture_output=True, text=True)
        log = Path(temporary) / 'initialization.log'
        result = subprocess.run([*java, '-Xlog:class+init=info:file=' + str(log), '-cp', str(classes) + ':' + str(jar),
            'syx.assistant.StockpileProtocolCheck'], check=True, timeout=30, capture_output=True, text=True)
        codec = json.loads(result.stdout)
        initialized = log.read_text()
        assert "Initializing 'game/GAME'" not in initialized
        assert "Initializing 'settlement/main/SETT'" not in initialized
        assert codec['accepted_frames'] == 7 and codec['rejected_frames'] == 41 and codec['predicate_checks'] == 150
    return {
        'passed': True, 'checked_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'Developer-only candidate compilation, strict wire parsing, integer comparisons and two public room lookup reader bodies. No collector execution, game fixture or MCP transport.',
        'game_jar_sha256': sha(jar), 'source_archive_sha256': sha(archive),
        'catalog_sha256': sha(catalog_path),
        'candidate_source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in candidates},
        'production_compilation_source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in production},
        'verifier_source_sha256': sha(Path(__file__)),
        'codec': codec, 'initialization_log_checked': ['game/GAME', 'settlement/main/SETT'],
        'management_route_review': {
            'sources': management, 'declared_public_full_view_methods': declared,
            'finding': 'The inspected manager current-view field is private; this concrete full-view class declares no public current-selection reader. No safe selected-tab mapping is established by this route.',
            'limit': 'Finite source/catalog inspection, not proof that every possible public route is unavailable.',
        },
        'room_lookup_members': [{
            'id': member, 'public': True, 'source_anchor': records[member]['source_candidates'][0],
            'normalized_disassembly_sha256': fingerprint(code), 'bounded_accessor_body': True,
            'documented_stable_contract': False,
        } for member, code in zip(required, body)],
        'limits': [
            'No player dispatch, mailbox, MCP schema/tool, response validation or retained capture is implemented.',
            'No runtime counter/identity/cursor/getter parity, removal/reuse, fault, scene or cost acceptance for this candidate.',
            'Room IDs are current array slots and may be reused; blueprint and anchor observations are not durable world identities.',
            'The earlier stockpile boundary/native reports keep their original source and finite fixture scopes.',
            'The candidate response currently lacks a serialized byte budget; production integration must enforce the paired 64 KiB all-or-error bound.',
            'Selected reader bodies are checked for direct writes, allocation, backward branches and expected reads, not whole-program equivalence.',
        ],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('game-dir', 'jdk-home', 'catalog', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.game_dir, args.jdk_home, args.catalog)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': report['passed'], 'codec': report['codec']}))
