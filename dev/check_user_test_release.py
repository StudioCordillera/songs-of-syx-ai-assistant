"""Check the shipped player bundle matches this checkout, without licensed game files."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from make_user_test import MODULES, digest


def check(root=ROOT):
    archive=root/'releases/latest-user-test.zip'
    metadata=json.loads((root/'releases/latest-user-test.json').read_text())
    assert metadata['download_sha256']==digest(archive),'Download hash differs'
    with zipfile.ZipFile(archive) as bundle:
        manifest=json.loads(bundle.read('BUILD.json'))
        assert metadata=={**manifest,'download_sha256':digest(archive)},'Manifest differs'
        assert len(bundle.namelist())==len(set(bundle.namelist())),'Duplicate archive entries'
        assert set(bundle.namelist())==set(manifest['files'])|{'BUILD.json'},'Unexpected archive entries'
        for name,expected in manifest['files'].items():
            assert hashlib.sha256(bundle.read(name)).hexdigest()==expected,'Archive content differs: '+name
        for module in MODULES:
            name=module+'.py'
            assert manifest['files'][name]==digest(root/name),'Rebuild user-test after changing '+name
        for path in (root/'user_test').iterdir():
            if path.is_file():
                assert manifest['files'][path.name]==digest(path),'Rebuild user-test after changing '+path.name
        assert manifest['builder_source_sha256']==digest(root/'build_mod.py'),'Builder changed'
        assert manifest['packager_source_sha256']==digest(root/'make_user_test.py'),'Packager changed'
        report=manifest['validation']
        assert report==json.loads((root/'USER_TEST_VALIDATION.json').read_text()),'Validation report differs'
        assert report['passed'] and report['real_provider_round_trip'] and report['requested_model']=='deepseek-v4-pro'
        sources={str(p.relative_to(root/'mod/src/main/java')):digest(p) for p in (root/'mod/src/main/java').rglob('*.java')}
        assert report['production_source_sha256']==sources,'Rebuild and validate changed game source'
        assert report['python_source_sha256']=={m+'.py':digest(root/(m+'.py')) for m in MODULES},'Python validation is stale'
        assert manifest['mod_jar_sha256']==report['mod_jar_sha256']==manifest['files']['mod/syx-ai-assistant/V71/script/syx-ai-assistant.jar']
        with zipfile.ZipFile(__import__('io').BytesIO(bundle.read('mod/syx-ai-assistant/V71/script/syx-ai-assistant.jar'))) as jar:
            assert all(n.startswith('syx/assistant/') and n.endswith('.class') for n in jar.namelist()),'Unexpected mod contents'
    return manifest


if __name__=='__main__':
    try:result=check()
    except (AssertionError,KeyError,ValueError,OSError,zipfile.BadZipFile) as error:
        raise SystemExit('Player release check failed: '+str(error))
    print('Player bundle matches current source and validated DeepSeek Pro build.')
