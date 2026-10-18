"""Review stockpile candidate getters in licensed files; never load or invoke game classes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'dev'))
from verify_bytecode import disassemble, method, fingerprint

BASE = 'settlement.room.infra.stockpile.'
FIELDS = ('crates', 'space', 'spaceReserved', 'amount', 'amountReserved')


def stored_reader(body, required=()):
    """Fail closed on direct writes/allocations/loops; not a transitive purity proof."""
    if re.search(r'\b(?:putfield|putstatic|[abilfdcs]astore|new|newarray|anewarray|multianewarray)\b', body):
        raise ValueError('Candidate reader contains a write/allocation opcode')
    for line in body.splitlines():
        branch = re.match(r'\s*(\d+):\s+(?:if\w*|goto(?:_w)?)\s+(\d+)', line)
        if branch and int(branch[2]) <= int(branch[1]):
            raise ValueError('Candidate reader contains a backward branch')
    if any(op in body for op in ('tableswitch', 'lookupswitch', 'invokedynamic')):
        raise ValueError('Candidate reader contains unreviewed dispatch')
    for marker in required:
        if marker not in body:
            raise ValueError('Expected stockpile reader marker missing: ' + marker)


def review(game, jdk, catalog_path):
    jar = game / 'SongsOfSyx.jar'
    archive = game / 'info/SongsOfSyx-sources.jar'
    game_hash = hashlib.sha256(jar.read_bytes()).hexdigest()
    archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
    raw_catalog = catalog_path.read_bytes()
    if len(raw_catalog) > 32 * 1024 * 1024:
        raise ValueError('Declaration catalog exceeds 32 MiB')
    catalog = json.loads(raw_catalog)
    if catalog['game_jar_sha256'] != game_hash or catalog['source_archive_sha256'] != archive_hash:
        raise ValueError('Catalog is not paired with the inspected game/source')
    ids = {m['id'] for m in catalog['members']}
    required_ids = [BASE+'ROOM_STOCKPILE#tally()', 'settlement.room.main.ROOMS#STOCKPILE']
    required_ids += [BASE+'StockpileTally#'+field for field in FIELDS]
    required_ids += [BASE+'StockpileTally.TallyData#'+s for s in
                    ['total(int)', 'get(int,settlement.room.infra.stockpile.StockpileInstance)']]
    if not set(required_ids) <= ids:
        raise ValueError('Candidate public route is absent from declaration catalog')
    java = ['java', '-Djava.home='+str(jdk.resolve())]
    cache = {}
    records = []
    bodies = {}
    declarations = [
        (BASE+'ROOM_STOCKPILE', 'public settlement.room.infra.stockpile.StockpileTally tally();', ('getfield', 'tally:')),
        (BASE+'StockpileTally$TallyData', 'public int total(int);', ('ams:[I', 'iaload', 'ireturn')),
        (BASE+'StockpileTally$TallyData', 'public int get(int, settlement.room.infra.stockpile.StockpileInstance);', ('StockpileInstance.tdata:[[I', 'aaload', 'iaload')),
        (BASE+'StockpileTally$TallyData', 'public int total(init.resources.RESOURCE);', ('RESOURCE.index:', 'RESOURCES.ALL:', 'iaload')),
        (BASE+'StockpileTally$TallyData', 'public int get(init.resources.RESOURCE, settlement.room.infra.stockpile.StockpileInstance);', ('RESOURCE.index:', 'RESOURCES.ALL:', 'aaload', 'iaload')),
        (BASE+'StockpileTally', 'public double load(init.resources.RESOURCE);', ('TallyData.total:', 'dconst_1', 'ddiv')),
        (BASE+'StockpileInstance', 'public double getUsedSpace();', ('StockpileTally.amount:', 'StockpileTally.space:', 'dconst_0', 'ddiv')),
        (BASE+'StockpileInstance', 'public double storedD(init.resources.RESOURCE);', ('StockpileTally.amountReserved:', 'isub', 'dconst_1', 'ddiv')),
    ]
    with zipfile.ZipFile(archive) as z:
        paths = ['settlement/room/infra/stockpile/StockpileTally.java',
                 'settlement/room/infra/stockpile/StockpileInstance.java',
                 'settlement/room/infra/stockpile/ROOM_STOCKPILE.java',
                 'settlement/room/main/job/StorageCrate.java']
        sources = {p: z.read(p) for p in paths}
        for owner, signature, markers in declarations:
            if owner not in cache:
                cache[owner] = disassemble(java, jar, owner)
            body = method(cache[owner], signature)
            stored_reader(body, markers)
            # The integer-index routes do not dispatch to another game method.
            if signature in ('public int total(int);', 'public int get(int, settlement.room.infra.stockpile.StockpileInstance);'):
                if re.search(r'\binvoke\w*\b', body):
                    raise ValueError('Integer tally getter gained a method invocation')
            bodies[signature] = body
            path = owner.split('$')[0].replace('.', '/')+'.java'
            records.append({'owner': owner, 'signature': signature, 'source_path': path,
                            'source_sha256': hashlib.sha256(sources[path]).hexdigest(),
                            'normalized_disassembly_sha256': fingerprint(body),
                            'direct_write_allocation_backward_branch_absent': True})
        tally = sources[paths[0]].decode()
        for expression in ['delta*ins.crateSize(cr.resource())', 'delta*cr.reservedSpace()',
                           'delta*cr.amount()', 'delta*cr.reserved()']:
            if expression not in tally:
                raise ValueError('Tally bookkeeping source changed; re-establish units')
        scratch_owner = 'settlement.room.main.job.StorageCrate'
        scratch = method(disassemble(java, jar, scratch_owner),
                         'public settlement.room.main.job.StorageCrate get(int, int, settlement.room.main.RoomInstance, settlement.room.main.job.StorageCrate$StorageData[]);')
        if len(re.findall(r'\bputfield\b', scratch)) != 4:
            raise ValueError('Crate scratch-object binding changed; re-review aliasing')
        records.append({'owner': scratch_owner, 'signature': 'get(int,int,RoomInstance,StorageData[])',
                        'source_path': paths[3], 'source_sha256': hashlib.sha256(sources[paths[3]]).hexdigest(),
                        'normalized_disassembly_sha256': fingerprint(scratch),
                        'scratch_field_write_count': 4, 'candidate_for_retained_handle': False})
    return {'passed': True, 'stage': 'static candidate review only; no new runtime mapping',
            'method': 'Licensed source plus selected javap bodies and paired public declaration metadata; no game execution, private runtime access or method invocation.',
            'game_jar_sha256': game_hash, 'source_archive_sha256': archive_hash,
            'catalog_sha256': hashlib.sha256(raw_catalog).hexdigest(),
            'candidate_public_route_members': required_ids, 'checks': records,
            'candidate_fields': {
                'crates': 'Assigned crate count for a resource, not capacity in resource items.',
                'space': 'Assigned capacity in resource items, from crate capacity bookkeeping.',
                'spaceReserved': 'Reserved incoming capacity in resource items, not physically stored goods.',
                'amount': 'Stored resource items in stockpile tally, including reserved stored items.',
                'amountReserved': 'Reserved stored resource items; separate from incoming space reservations.'},
            'conclusions': [
                'Prefer explicit integer-index tally reads on validated installed-resource indexes, inside one game after-update callback. Total reads use one array access; per-room reads use two. No reader traversal or direct write is present in these reviewed bodies.',
                'Stockpile totals are not RESOURCE.owned(): the latter mixes additional logistics locations, incoming station goods and trade promises.',
                'Room getUsedSpace returns zero at zero assigned capacity. Resource load and storedD return one at zero capacity; storedD subtracts reserved stored items. These getters are not interchangeable fullness percentages.',
                'Crate coordinate reads bind four fields on a shared scratch object. Never retain or expose that live handle. The narrower tally route avoids invoking the crate binder.',
                'Per-room totals and cross-room sums still need lifecycle, activation/deactivation and direct getter parity in an isolated city before production exposure.'],
            'verifier_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'limits': ['Shipped-source verification, not a documented stable official mod contract or complete call-graph proof.',
                       'Catalog access is compiler-checked discovery metadata, not runtime safety or a count of supported variables.',
                       'No runtime getter/MCP parity, observed reservations, cap/fault or cost measurements; no new public members added to production.',
                       'No claim about all warehouses, stock on the ground, goods in transit, reservations completing, food sufficiency, exact tally age or UI-selected room.',
                       'Future mappings must be city-only unless other scenes are established, bounded by resource/room/row budgets, detached and explicit about failures/truncation; never sum capacity across heterogeneous resources as a meaningful fullness ratio.']}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('game-dir', 'jdk-home', 'catalog', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    result = review(a.game_dir, a.jdk_home, a.catalog)
    a.output.write_text(json.dumps(result, indent=2)+'\n')
    print('Stockpile candidate boundary review passed; no game process started or runtime mapping added.')
