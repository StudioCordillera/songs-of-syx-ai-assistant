"""Build a metadata-only discovery catalog; never executes game code or establishes getter safety."""
import argparse
from collections import Counter
import json
import hashlib
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent


def catalog(game_dir: Path, output: Path):
    jar = game_dir / 'SongsOfSyx.jar'
    sources = game_dir / 'info/SongsOfSyx-sources.jar'
    if not jar.is_file() or not sources.is_file():
        raise ValueError('The licensed game JAR and shipped source archive are required')
    java = ['java']
    if os.environ.get('SYX_JAVA_HOME'):
        java += ['-Djava.home=' + os.environ['SYX_JAVA_HOME']]
    classes = ROOT / 'build/catalog'
    classes.mkdir(parents=True, exist_ok=True)
    subprocess.run([*java, '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '17', '-d', str(classes),
                    str(ROOT / 'dev/GameApiCatalog.java'),
                    str(ROOT / 'mod/src/main/java/syx/assistant/JsonWriter.java')], check=True)
    subprocess.run([*java, '-Xmx2g', '-cp', str(classes), 'syx.dev.GameApiCatalog',
                    str(jar), str(sources), str(output)], check=True)
    data = json.loads(output.read_text())
    counts = Counter(row['owner'].split('.')[0] for row in data['members'])
    anchors = Counter(row['source_match'] for row in data['members'])
    summary = {key: data[key] for key in ('schema_version', 'game_jar_sha256', 'source_archive_sha256', 'source_files', 'warning')}
    summary['catalog_sha256'] = hashlib.sha256(output.read_bytes()).hexdigest()
    audit_path = ROOT / 'api-audit.json'
    if audit_path.exists():
        audit = json.loads(audit_path.read_text())
        paired = all(audit.get(key) == data[key] for key in ('game_jar_sha256', 'source_archive_sha256'))
        summary['production_audit_paired'] = paired
        if paired:
            catalog_ids = {row['id'] for row in data['members']}
            summary['production_reference_count'] = len(audit['members'])
            summary['production_references_found'] = sum(row['id'] in catalog_ids for row in audit['members'])
            summary['production_references_by_root_package'] = dict(sorted(Counter(row['owner'].split('.')[0] for row in audit['members']).items()))
    summary.update(public_type_count=len(data['public_types']), public_declared_member_count=len(data['members']),
                   members_by_root_package=dict(sorted(counts.items())), source_matches=dict(anchors),
                   unresolved_source_type_count=len(data['unresolved_source_types']))
    output.with_suffix('.summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


def search_catalog(path: Path, query: str, offset=0, limit=10):
    if len(query) > 500 or type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 30:
        raise ValueError('Query up to 500 characters; offset >=0 and limit 1..30')
    if path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError('Catalog exceeds 32 MiB')
    data = json.loads(path.read_text())
    terms = query.casefold().split()
    rows = [row for row in data['members'] if all(term in (row['id'] + ' ' + row['value_type']).casefold() for term in terms)]
    result = {'members': rows[offset:offset + limit], 'total': len(rows),
              'next_offset': offset + limit if offset + limit < len(rows) else None,
              'game_jar_sha256': data['game_jar_sha256'], 'warning': data['warning']}
    if len(json.dumps(result).encode()) > 65536:
        raise ValueError('Metadata result exceeds 64 KiB; reduce limit')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/game-api-catalog.json')
    parser.add_argument('--query', help='Search existing output instead of building it; metadata only')
    parser.add_argument('--offset', type=int, default=0)
    parser.add_argument('--limit', type=int, default=10)
    args = parser.parse_args()
    if args.query is not None:
        result = search_catalog(args.output, args.query, args.offset, args.limit)
    elif args.game_dir is not None:
        result = catalog(args.game_dir, args.output)
    else:
        parser.error('--game-dir is required to build; --query searches an existing output')
    print(json.dumps(result, indent=2))
