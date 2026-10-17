"""Verify discovery boundaries against compiled synthetic APIs, independently of the game."""
import json
import os
from pathlib import Path
import subprocess
from zipfile import ZipFile

from catalog_api import catalog


def test_catalog_compiler_access_source_anchors_and_no_execution(tmp_path):
    java = ['java']
    if os.environ.get('SYX_JAVA_HOME'):
        java += ['-Djava.home=' + os.environ['SYX_JAVA_HOME']]
    source = tmp_path / 'source/fixture'
    source.mkdir(parents=True)
    api = source / 'Api.java'
    api.write_text('''package fixture;
public class Api extends Base {
    public static final String TRAP = fail();
    private static String fail() {throw new AssertionError("Game classes must never execute");}
    /** A comment is not a stable getter contract. */
    public String read(String value) {return value;}
    public int read(int value) {return value;}
    private int secret;
    public static class Nested {public int value;}
    static class Hidden {public int secret; public static class PublicInsideHidden {public int secret;}}
    public interface Contract {int COUNT = 1; String name();}
    public enum Mode {ONE;}
}
''')
    base = source / 'Base.java'
    base.write_text('package fixture; public class Base {public int inherited;}')
    classes = tmp_path / 'classes'
    classes.mkdir()
    subprocess.run([*java, '-m', 'jdk.compiler/com.sun.tools.javac.Main', '-d', str(classes), str(api), str(base)], check=True)
    game = tmp_path / 'game'
    (game / 'info').mkdir(parents=True)
    subprocess.run([*java, '-m', 'jdk.jartool/sun.tools.jar.Main', '--create', '--file', str(game / 'SongsOfSyx.jar'), '-C', str(classes), '.'], check=True)
    with ZipFile(game / 'info/SongsOfSyx-sources.jar', 'w') as archive:
        archive.write(api, 'fixture/Api.java')
        archive.write(base, 'fixture/Base.java')
    output = tmp_path / 'catalog.json'
    summary = catalog(game, output)
    data = json.loads(output.read_text())
    by_id = {m['id']: m for m in data['members']}
    assert summary['unresolved_source_type_count'] == 0
    assert {t['name'] for t in data['public_types']} == {
        'fixture.Api', 'fixture.Base', 'fixture.Api.Nested', 'fixture.Api.Contract', 'fixture.Api.Mode'}
    assert not any('Hidden' in key or 'secret' in key or 'fail(' in key for key in by_id)
    assert 'fixture.Base#inherited' in by_id and 'fixture.Api#inherited' not in by_id
    for signature in ('read(java.lang.String)', 'read(int)'):
        member = by_id['fixture.Api#' + signature]
        assert len(member['source_candidates']) == 1
        assert member['source_candidates'][0]['line'] > 0
        assert len(member['source_candidates'][0]['source_sha256']) == 64
    assert by_id['fixture.Api#read(java.lang.String)']['source_candidates'][0]['has_javadoc']
    assert 'fixture.Api.Contract#name()' in by_id and 'fixture.Api.Contract#COUNT' in by_id
    assert by_id['fixture.Api.Mode#values()']['source_match'] == 'no_exact_source_anchor'
    assert 'method bodies' in summary['warning']
    assert 'Game classes must never execute' not in output.read_text()
    assert 'A comment is not' not in output.read_text()
