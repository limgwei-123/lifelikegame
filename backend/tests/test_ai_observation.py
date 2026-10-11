from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.ai_planner.observation import CallObservation, TokenUsage, safe_observe


def test_observation_preserves_null_zero_and_invalid_counters():
    usage = TokenUsage(prompt_tokens=0, output_tokens=None, total_tokens=True,
                       cached_input_tokens=-1, thinking_tokens=2**63, tool_input_tokens="2")
    assert usage.prompt_tokens == 0
    assert all(getattr(usage, key) is None for key in (
        "output_tokens", "total_tokens", "cached_input_tokens", "thinking_tokens", "tool_input_tokens",
    ))


def test_observation_monotonic_latency_and_single_snapshot():
    now = [datetime(2026, 10, 11, tzinfo=timezone.utc)]
    timer = [10.0]
    observation = CallObservation(clock=lambda: now[0], timer=lambda: timer[0])
    assert observation.snapshot() is None
    observation.begin_dispatch()
    observation.attempt()
    observation.attempt()
    observation.capture_usage(TokenUsage(prompt_tokens=5))
    timer[0] = 10.25
    now[0] -= timedelta(seconds=1)
    observation.finish()
    timer[0] = 99
    observation.finish()
    snapshot = observation.snapshot()
    assert snapshot.latency_ms == Decimal("250.000")
    assert (snapshot.attempts, snapshot.retry_count) == (2, 1)
    assert snapshot.finished_at < snapshot.started_at
    assert snapshot.tokens.total_tokens is None


def test_no_http_instrumentation_means_unknown_attempts():
    observation = CallObservation()
    observation.begin_dispatch()
    observation.finish()
    assert observation.snapshot().attempts is None


def test_failed_attempt_hook_marks_coverage_unknown(monkeypatch, caplog):
    observation = CallObservation()
    observation.begin_dispatch()
    observation.attempt()
    monkeypatch.setattr(observation, "attempt", lambda: (_ for _ in ()).throw(ValueError("PRIVATE")))
    safe_observe(observation, "attempt")
    observation.finish()
    assert observation.snapshot().attempts is None
    assert "PRIVATE" not in caplog.text


def test_safe_observer_never_swallows_process_exit(monkeypatch):
    observation = CallObservation()
    monkeypatch.setattr(observation, "finish", lambda: (_ for _ in ()).throw(KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt):
        safe_observe(observation, "finish")
