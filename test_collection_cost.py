"""Profiling failures must restore only the disposable mod and detect changed saves."""
import pytest
from dev.profile_collection_cost import copied_mod


@pytest.fixture
def paths(tmp_path):
    home=tmp_path/'smoke-home'
    target=home/'.local/share/songsofsyx/mods/syx-ai-assistant/V71/script/syx-ai-assistant.jar'
    target.parent.mkdir(parents=True);target.write_bytes(b'prior copied mod')
    save=tmp_path/'smoke.save';save.write_bytes(b'copied save')
    jar=tmp_path/'candidate.jar';jar.write_bytes(b'candidate mod')
    state=tmp_path/'state';state.mkdir()
    return home,target,save,jar,state


@pytest.mark.parametrize('fail',[False,True])
def test_copied_mod_restores_after_success_or_fixture_failure(paths,fail):
    home,target,save,jar,state=paths
    def run():
        with copied_mod(home,save,jar,state):
            assert target.read_bytes()==b'candidate mod'
            if fail:raise TimeoutError('native fixture timed out')
    if fail:
        with pytest.raises(TimeoutError):run()
    else:run()
    assert target.read_bytes()==b'prior copied mod'
    assert save.read_bytes()==b'copied save'


def test_copied_mod_refuses_success_when_save_changed(paths):
    home,target,save,jar,state=paths
    with pytest.raises(RuntimeError,match='save integrity'):
        with copied_mod(home,save,jar,state):save.write_bytes(b'unexpected fixture save change')
    assert target.read_bytes()==b'prior copied mod'


@pytest.mark.parametrize('parent_escape',[False,True])
def test_copied_mod_refuses_symlink_to_other_profile(paths,parent_escape):
    home,target,save,jar,state=paths
    other=state/'other-mod.jar';other.write_bytes(b'other profile')
    target.unlink()
    if parent_escape:
        target.parent.rmdir();target.parent.symlink_to(state,target_is_directory=True)
        (state/target.name).write_bytes(b'other profile')
    else:target.symlink_to(other)
    with pytest.raises(ValueError,match='stay inside'):
        with copied_mod(home,save,jar,state):pytest.fail('Unsafe fixture accepted')
    assert other.read_bytes()==b'other profile'
    assert not (state/'prior-mod.jar').exists()
