"""Actual owned process termination across committed coordinator/history boundaries."""
import pytest
from dev.check_chat_process_recovery import STAGES, run_case


@pytest.mark.parametrize('stage', STAGES)
def test_owned_process_crash_recovery_never_resubmits_original_action(stage):
    result = run_case(stage)
    assert result['owned_child_sigkill_verified']
    assert result['separate_resume_process']
    assert result['old_action_acknowledged_without_new_turn_or_provider']
    assert result['automatic_sync_selected_original_chat']
    assert result['new_explicit_turn_completed_with_fresh_context']
    assert result['new_fake_provider_calls'] == 1
