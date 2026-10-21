"""Finite cross-language interaction policy traces; no native game or provider."""
from dev.verify_gesture_reducer import verify


def test_detached_java_reducer_matches_python_and_independent_policy_traces(tmp_path):
    report=verify(tmp_path)
    assert report['passed'] and report['trace_steps']>2000
    assert report['independently_authored_expected_steps']>=25
    assert report['seeded_gesture_scenarios']==200
    assert report['game_calls']==report['native_input_calls']==report['provider_calls']==0
