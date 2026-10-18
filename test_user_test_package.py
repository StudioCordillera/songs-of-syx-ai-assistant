"""Promotion/rollback tests use synthetic mod payloads, never claim game validation."""
import importlib.util
import json
from pathlib import Path
import sys
import zipfile
import pytest
import make_user_test as release


def fixture_report(tmp_path,content=b'synthetic class'):
    mod=tmp_path/'mod';jar=mod/'V71/script/syx-ai-assistant.jar';jar.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(jar,'w') as z:z.writestr('syx/assistant/Fixture.class',content)
    (mod/'_Info.txt').write_text('synthetic metadata')
    report={'passed':True,'real_provider_round_trip':True,'requested_model':'deepseek-v4-pro',
        'mod_jar_sha256':release.digest(jar),'production_source_sha256':{str(p.relative_to(release.ROOT/'mod/src/main/java')):release.digest(p) for p in (release.ROOT/'mod/src/main/java').rglob('*.java')},
        'python_source_sha256':{n+'.py':release.digest(release.ROOT/(n+'.py')) for n in release.MODULES}}
    path=tmp_path/'validation.json';path.write_text(json.dumps(report))
    return jar,path,report


def test_player_package_preserves_last_working_build_and_rejects_stale_sources(tmp_path):
    jar,report_path,report=fixture_report(tmp_path)
    output=tmp_path/'releases';latest=release.package(jar,report_path,output);original=latest.read_bytes()
    with zipfile.ZipFile(latest) as z:
        assert {'README.txt','start-chat.sh','player.py','install-mod.py','BUILD.json','mod/syx-ai-assistant/V71/script/syx-ai-assistant.jar'}<=set(z.namelist())
        assert not any(n.endswith('.env') or '.venv/' in n or 'SongsOfSyx.jar' in n for n in z.namelist())
        assert z.getinfo('start-chat.sh').external_attr>>16 & 0o111
    report['python_source_sha256']['syx_chat_service.py']='wrong';report_path.write_text(json.dumps(report))
    with pytest.raises(ValueError,match='source changed'):release.package(jar,report_path,output)
    assert latest.read_bytes()==original
    jar,report_path,_=fixture_report(tmp_path,b'second synthetic class')
    release.package(jar,report_path,output)
    assert (output/'previous-user-test.zip').read_bytes()==original
    assert latest.read_bytes()!=original


def test_mod_installer_rolls_back_copy_failure_without_touching_saves(tmp_path,monkeypatch):
    bundle=tmp_path/'bundle';bundle.mkdir()
    source=release.ROOT/'user_test/install-mod.py';copied=bundle/'install-mod.py';copied.write_bytes(source.read_bytes())
    new=bundle/'mod/syx-ai-assistant/V71/script';new.mkdir(parents=True);(new/'syx-ai-assistant.jar').write_bytes(b'candidate')
    profile=tmp_path/'profile';old=profile/'mods/syx-ai-assistant';old.mkdir(parents=True);(old/'old.txt').write_text('working')
    save=profile/'save.save';save.write_text('untouched')
    spec=importlib.util.spec_from_file_location('fixture_install',copied);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(sys,'argv',['install-mod.py','--user-dir',str(profile)])
    def fail(*args,**kwargs):raise OSError('simulated disk error')
    monkeypatch.setattr(module.shutil,'copytree',fail)
    with pytest.raises(OSError):module.main()
    assert (old/'old.txt').read_text()=='working' and save.read_text()=='untouched'
