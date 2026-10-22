"""Real helper entry point/MCP subprocess lifecycle with authored state, no key/game."""
from dev.check_helper_lifecycle import run


def test_helper_history_lock_and_real_stdio_restart_without_credentials():
    report = run()
    assert report['passed']
    assert report['successful_helper_and_stdio_mcp_startups'] == 2
    assert report['history_lock_contender_refused_before_recovery']
    assert report['startup_recovered_authored_running_rows'] == 2
    assert report['missing_key_send_rejected_without_turn_or_event']
    assert report['external_inference_calls'] == 0
