"""Reject known engine-crash paths that can still return process exit code zero."""
from pathlib import Path


def require_clean_game_log(path):
    """Finite log-marker guard, not proof that every possible game failure is detected."""
    # Errors.check() also captures ordinary fixture stderr on normal shutdown.
    # SMOKE_CAPTURED_ENGINE_OUTPUT alone is therefore not a failure marker.
    text=Path(path).read_text(encoding='utf-8',errors='replace')
    if any(marker in text for marker in ['Time until crash:','SMOKE_FIXTURE_FAILURE:','A fatal error has been detected by the Java Runtime Environment:']):
        raise RuntimeError('Engine crash/error marker despite process completion; inspect the private game log')
