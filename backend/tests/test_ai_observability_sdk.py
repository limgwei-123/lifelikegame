import json

import httpx
import pytest

from app.ai_planner.errors import AIQuotaExceededError
from app.ai_planner.observation import CallObservation
from app.ai_planner.providers import gemini
from app.ai_planner.providers.base import PlannerRequest, PlannerResult
from app.errors.exception import AppError
from test_ai_failures import sdk_transport
from test_ai_pricing import sample_snapshot


def wire_response(text=None, **metadata):
    return {"candidates": [{"content": {"parts": [{"text": text if text is not None else json.dumps({
        "status": "need_more_info", "message": "When?",
    })}]}}], "usageMetadata": metadata}


def generate(observation, before_send=None):
    return gemini.GeminiPlannerProvider(api_key="PRIVATE-KEY", model="test-model", observation=observation,
                                      before_send=before_send).generate_plan(
        PlannerRequest(user_prompt="PRIVATE PROMPT", conversation_history=[]),
    )


def test_sdk_success_observes_usage_and_one_attempt(sdk_transport):
    sdk_transport[0].append(wire_response(promptTokenCount=1000, candidatesTokenCount=100,
                                         totalTokenCount=1150, cachedContentTokenCount=200,
                                         thoughtsTokenCount=50, toolUsePromptTokenCount=0))
    observation = CallObservation()
    assert generate(observation).message == "When?"
    snapshot = observation.snapshot()
    assert (snapshot.attempts, snapshot.retry_count) == (1, 0)
    assert snapshot.tokens == sample_snapshot().tokens
    assert snapshot.latency_ms >= 0
    assert sdk_transport[2][0]._api_client._httpx_client.is_closed


def test_sdk_retry_recovery_observes_three_attempts_one_snapshot(sdk_transport):
    sdk_transport[0].extend([503, 503, wire_response(promptTokenCount=10, candidatesTokenCount=2)])
    observation = CallObservation()
    generate(observation)
    assert observation.snapshot().attempts == 3
    assert observation.snapshot().retry_count == 2
    assert observation.snapshot().tokens.prompt_tokens == 10
    assert len(sdk_transport[1]) == 3


@pytest.mark.parametrize("outcome,code,attempts", [
    (httpx.ReadTimeout("PRIVATE"), "AI_TIMEOUT", 3),
    (429, "AI_RATE_LIMITED", 3),
    (wire_response(text="PRIVATE invalid JSON", promptTokenCount=10), "AI_INVALID_OUTPUT", 1),
])
def test_provider_failures_still_finish_observation(sdk_transport, outcome, code, attempts):
    sdk_transport[0].append(outcome)
    observation = CallObservation()
    with pytest.raises(AppError) as error:
        generate(observation)
    assert error.value.code == code
    snapshot = observation.snapshot()
    assert snapshot.attempts == attempts
    assert snapshot.tokens.prompt_tokens == (10 if code == "AI_INVALID_OUTPUT" else None)
    assert sdk_transport[2][0]._api_client._httpx_client.is_closed


def test_missing_metadata_does_not_manufacture_token_counts(sdk_transport):
    sdk_transport[0].append(json.dumps({"status": "need_more_info", "message": "When?"}))
    observation = CallObservation()
    generate(observation)
    assert observation.snapshot().tokens.prompt_tokens is None
    assert "observation" not in PlannerResult.model_json_schema()["properties"]


def test_quota_rejection_never_starts_observation_or_dispatches(sdk_transport):
    observation = CallObservation()
    error = AIQuotaExceededError(sample_snapshot().finished_at)

    def reject():
        raise error

    with pytest.raises(AIQuotaExceededError) as caught:
        generate(observation, reject)
    assert caught.value is error
    assert observation.snapshot() is None
    assert not sdk_transport[1]
    assert sdk_transport[2][0]._api_client._httpx_client.is_closed


@pytest.mark.parametrize("method", ["begin_dispatch", "attempt", "capture_usage", "finish"])
def test_observer_failure_does_not_change_sdk_behavior(sdk_transport, monkeypatch, caplog, method):
    sdk_transport[0].append(wire_response(promptTokenCount=10))
    observation = CallObservation()

    def fail(*args):
        raise ValueError("PRIVATE observer failure")

    monkeypatch.setattr(observation, method, fail)
    assert generate(observation).message == "When?"
    assert len(sdk_transport[1]) == 1
    assert "PRIVATE" not in caplog.text
    if method == "attempt":
        assert observation.snapshot().attempts is None


def test_existing_http_hooks_are_composed(sdk_transport, monkeypatch):
    sdk_transport[0].extend([503, wire_response(promptTokenCount=10)])
    original_factory = gemini.genai.Client
    seen = []

    def factory(**kwargs):
        options = kwargs["http_options"]
        hooks = options.client_args["event_hooks"]
        hooks["request"].append(lambda request: seen.append(True))
        return original_factory(**kwargs)

    monkeypatch.setattr(gemini.genai, "Client", factory)
    observation = CallObservation()
    generate(observation)
    assert seen == [True, True]
    assert observation.snapshot().attempts == 2
