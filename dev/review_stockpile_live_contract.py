"""Pin the additional public warehouse-slot reader implementation, without starting the game."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from verify_bytecode import disassemble, method, fingerprint
from review_stockpile_boundary import stored_reader


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def review(game,jdk,catalog_path):
    jar=game/'SongsOfSyx.jar';archive=game/'info/SongsOfSyx-sources.jar'
    prior=json.loads((ROOT/'STOCKPILE_BOUNDARY_REVIEW.json').read_text())
    assert prior['passed'] and prior['game_jar_sha256']==sha(jar) and prior['source_archive_sha256']==sha(archive)
    assert catalog_path.stat().st_size<=32*1024*1024
    catalog=json.loads(catalog_path.read_text());assert catalog['game_jar_sha256']==sha(jar) and catalog['source_archive_sha256']==sha(archive)
    ids={m['id']:m for m in catalog['members']}
    required=['settlement.room.main.RoomsMap#getByIndex(int)','settlement.room.main.RoomsMap#max()',
        'settlement.room.main.RoomBlueprintIns#all()','snake2d.util.sets.LIST#get(int)',
        'snake2d.util.sets.ArrayListResize#get(int)','snake2d.util.sets.ArrayListResize#size()']
    assert all(i in ids and 'public' in ids[i]['modifiers'] for i in required)
    sources={}
    with zipfile.ZipFile(archive) as z:
        for i in required:
            candidates=ids[i]['source_candidates'];assert len(candidates)==1
            c=candidates[0];raw=z.read(c['source_file']);assert hashlib.sha256(raw).hexdigest()==c['source_sha256']
            sources[c['source_file']]=c['source_sha256']
        blueprint=z.read('settlement/room/main/RoomBlueprintIns.java').decode()
        assert re.search(r'private\s+final\s+ArrayListResize<T>\s+all\s*=\s*new\s+ArrayListResize<T>\(128\)',blueprint)
    java=['java','-Djava.home='+str(jdk.resolve())]
    checks=[]
    for owner,signature,markers in [
        ('settlement.room.main.RoomsMap','public settlement.room.main.Room getByIndex(int);',('rooms:', 'aaload','areturn')),
        ('settlement.room.main.RoomsMap','public int max();',('rooms:','arraylength','ireturn')),
        ('settlement.room.main.RoomBlueprintIns','public final snake2d.util.sets.LIST<T> all();',('all:Lsnake2d/util/sets/ArrayListResize;','areturn')),
        ('snake2d.util.sets.ArrayListResize','public int size();',('last:I','ireturn')),
    ]:
        code=method(disassemble(java,jar,owner),signature);stored_reader(code,markers)
        assert not re.search(r'\binvoke\w*\b',code)
        checks.append({'owner':owner,'signature':signature,'normalized_disassembly_sha256':fingerprint(code),
            'checked_scope':'Full selected accessor body: expected primitive/array reads, no calls/direct writes/allocations/backward branches.'})
    code=method(disassemble(java,jar,'snake2d.util.sets.ArrayListResize'),'public E get(int);')
    cut=re.search(r'\bareturn\b',code);assert cut
    prefix=code[:cut.end()];stored_reader(prefix,('last:I','if_icmpge','es:[Ljava/lang/Object;','aaload','areturn'))
    assert not re.search(r'\binvoke\w*\b',prefix)
    assert 'NoSuchElementException' in code[cut.end():] and 'athrow' in code[cut.end():]
    checks.append({'owner':'snake2d.util.sets.ArrayListResize','signature':'public E get(int);',
        'normalized_disassembly_sha256':fingerprint(code),'checked_scope':'Valid indexed-read path only: size guard then stored array access, no call/write/allocation. Invalid-index path constructs and throws an exception; not claimed allocation-free.'})
    return {'passed':True,'checked_at':datetime.now(timezone.utc).isoformat(),'game_jar_sha256':sha(jar),'source_archive_sha256':sha(archive),
        'catalog_sha256':sha(catalog_path),'prior_tally_contract_review_sha256':sha(ROOT/'STOCKPILE_BOUNDARY_REVIEW.json'),
        'source_files_sha256':sources,'public_route_members':[{'id':i,'source_anchor':ids[i]['source_candidates'][0]} for i in required],
        'checks':checks,'verifier_source_sha256':sha(Path(__file__)),
        'conclusions':['The final typed warehouse blueprint inherits a final all() getter backed by its private final ArrayListResize instance list. Static inspection does not access that private field at runtime.',
            'The production page indexes only nonnegative slots below the same-callback list size. Removal/reordering between pages remains possible; row IDs/anchors are observation-scoped.',
            'Explicit IDs use public max() before getByIndex(), then require a current StockpileInstance with matching blueprint. Array slots can be reused; this is not durable identity.',
            'The existing paired tally review establishes five integer-index stored-counter readers; this extension adds discovery/explicit lookup routes, not crate scratch handles or gameplay commands.'],
        'limits':['Shipped-source/binary reader verification, not separately documented stable official mod contracts or complete source/binary equivalence.',
            'No game initialized or native/MCP acceptance added by this static verifier. See separately pinned STOCKPILE_LIVE_VALIDATION.json.',
            'Valid ArrayListResize.get path is allocation-free; invalid-index exception construction is explicitly excluded from that claim.',
            'No all-state/menu, permanent identity, selection inference, large-world cost, actual cap/fault or counter-age guarantee.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['game-dir','jdk-home','catalog','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();report=review(a.game_dir,a.jdk_home,a.catalog);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print('Public warehouse slot/tally contract review passed without game initialization.')
