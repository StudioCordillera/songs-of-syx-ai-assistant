"""Copied-fixture restoration must finish before a passing core report is published."""
from pathlib import Path
from types import SimpleNamespace
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parent/'dev'))
import verify_current_player_core as runner


def fixture(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'ROOT',tmp_path)
    runtime=tmp_path/'runtime';runtime.mkdir()
    target=runtime/'smoke-home/.local/share/songsofsyx/mods/syx-ai-assistant/V71/script/syx-ai-assistant.jar'
    target.parent.mkdir(parents=True);target.write_bytes(b'prior copied mod')
    save=runtime/'copy.save';save.write_bytes(b'copied save')
    output=runtime/'evidence';output.mkdir()
    return target,save,output,SimpleNamespace(save=save)


def test_core_report_follows_restoration(tmp_path,monkeypatch):
    target,save,output,args=fixture(tmp_path,monkeypatch)
    def inner(_):
        target.write_bytes(b'candidate')
        return output,{'passed':True}
    monkeypatch.setattr(runner,'verify_inner',inner)
    runner.verify(args)
    assert target.read_bytes()==b'prior copied mod'
    assert save.read_bytes()==b'copied save'
    report=(output/'player-core-validation.json').read_text()
    assert '"copied_mod_restored": true' in report and '"copied_save_unchanged": true' in report


def test_core_failure_restores_mod_without_report(tmp_path,monkeypatch):
    target,save,output,args=fixture(tmp_path,monkeypatch)
    def inner(_):
        target.write_bytes(b'candidate')
        raise RuntimeError('fixture failed')
    monkeypatch.setattr(runner,'verify_inner',inner)
    with pytest.raises(RuntimeError,match='fixture failed'):runner.verify(args)
    assert target.read_bytes()==b'prior copied mod'
    assert not (output/'player-core-validation.json').exists()


def test_save_integrity_failure_cannot_publish_success(tmp_path,monkeypatch):
    target,save,output,args=fixture(tmp_path,monkeypatch)
    def inner(_):
        target.write_bytes(b'candidate');save.write_bytes(b'changed copied save')
        return output,{'passed':True}
    monkeypatch.setattr(runner,'verify_inner',inner)
    with pytest.raises(RuntimeError,match='integrity failed'):runner.verify(args)
    assert target.read_bytes()==b'prior copied mod'
    assert not (output/'player-core-validation.json').exists()
