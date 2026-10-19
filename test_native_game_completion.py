from pathlib import Path
import pytest
from dev.native_game_completion import require_clean_game_log


@pytest.mark.parametrize('marker',['Time until crash:','SMOKE_FIXTURE_FAILURE:','A fatal error has been detected by the Java Runtime Environment:'])
def test_exit_zero_engine_failure_marker_is_not_accepted(tmp_path,marker):
    log=tmp_path/'game.log';log.write_text('all observations verified\n'+marker+' renderer/update error\nDISPOSING\n')
    with pytest.raises(RuntimeError,match='Engine crash/error marker'):require_clean_game_log(log)


def test_expected_request_refusal_and_normal_disposal_are_not_engine_crashes(tmp_path):
    log=tmp_path/'game.log';log.write_text('Request rejected: java.lang.IllegalArgumentException\nSMOKE_CAPTURED_ENGINE_OUTPUT: SMOKE: loading copied save on updater thread\nCore was successfully disposed\n')
    require_clean_game_log(log)
