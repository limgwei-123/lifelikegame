import json

import httpx
import pytest
from google.genai import Client

from app.ai_planner.providers import gemini
from app.ai_planner.providers.base import PlannerRequest
from app.errors.exception import AppError


@pytest.fixture
def sdk_transport(monkeypatch):
    clients = []
    calls = []
    outcomes = []

    def handle(request):
        calls.append(request)
        outcome = outcomes[min(len(calls) - 1, len(outcomes) - 1)]
        if isinstance(outcome, Exception):
            raise outcome
        if isinstance(outcome, int):
            return httpx.Response(outcome, json={"error": {"code": outcome, "message": "SECRET vendor details"}})
        if isinstance(outcome, dict):
            return httpx.Response(200, json=outcome)
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": outcome}]}}]})

    def build(**kwargs):
        options = kwargs["http_options"]
        assert options.timeout == 20000
        assert options.retry_options.attempts == 3
        options.client_args = {**(options.client_args or {}), "transport": httpx.MockTransport(handle)}
        client = Client(**kwargs)
        # Exercise real SDK retry predicates/counts without waiting between attempts.
        client._api_client._retry.sleep = lambda seconds: None
        clients.append(client)
        return client

    monkeypatch.setattr(gemini.genai, "Client", build)
    yield outcomes, calls, clients
    for client in clients:
        client.close()


def generate():
    return gemini.GeminiPlannerProvider(api_key="test-key", model="test-model").generate_plan(
        PlannerRequest(user_prompt="Fitness", conversation_history=[]),
    )


@pytest.mark.parametrize("failure,code,status,attempts", [
    (httpx.ReadTimeout("SECRET"), "AI_TIMEOUT", 504, 3),
    (httpx.ConnectError("SECRET"), "AI_UNAVAILABLE", 503, 3),
    (408, "AI_TIMEOUT", 504, 3),
    (429, "AI_RATE_LIMITED", 429, 3),
    (500, "AI_UNAVAILABLE", 503, 3),
    (502, "AI_UNAVAILABLE", 503, 3),
    (503, "AI_UNAVAILABLE", 503, 3),
    (504, "AI_TIMEOUT", 504, 3),
    (400, "AI_PROVIDER_ERROR", 502, 1),
    (401, "AI_CONFIGURATION_ERROR", 503, 1),
    (403, "AI_CONFIGURATION_ERROR", 503, 1),
    (404, "AI_CONFIGURATION_ERROR", 503, 1),
    (501, "AI_PROVIDER_ERROR", 502, 1),
    ("Not JSON SECRET", "AI_INVALID_OUTPUT", 502, 1),
    ("", "AI_INVALID_OUTPUT", 502, 1),
    ('{"status":"plan_ready","message":"SECRET"}', "AI_INVALID_OUTPUT", 502, 1),
])
def test_failures_have_bounded_attempts_and_safe_domain_errors(sdk_transport, failure, code, status, attempts):
    outcomes, calls, clients = sdk_transport
    outcomes.append(failure)
    with pytest.raises(AppError) as caught:
        generate()
    assert caught.value.code == code
    assert caught.value.status_code == status
    assert caught.value.details == {}
    assert "SECRET" not in str(caught.value)
    assert len(calls) == attempts
    assert calls[0].extensions["timeout"]["read"] == 20
    assert clients[0]._api_client._httpx_client.is_closed


@pytest.mark.parametrize("failure", [429, 503, httpx.ReadTimeout("timeout")])
def test_temporary_failure_can_recover(sdk_transport, failure):
    outcomes, calls, clients = sdk_transport
    outcomes.extend([failure, json.dumps({"status": "need_more_info", "message": "When?"})])
    assert generate().message == "When?"
    assert len(calls) == 2
    assert clients[0]._api_client._httpx_client.is_closed


def test_missing_configuration_never_creates_client(monkeypatch):
    monkeypatch.setattr(gemini.genai, "Client", lambda **kwargs: pytest.fail("Must not create client"))
    with pytest.raises(AppError) as caught:
        gemini.GeminiPlannerProvider(api_key=None, model=None).generate_plan(
            PlannerRequest(user_prompt="Hi", conversation_history=[]),
        )
    assert caught.value.code == "AI_CONFIGURATION_ERROR"


@pytest.mark.parametrize("code,status", [("AI_TIMEOUT", 504), ("AI_RATE_LIMITED", 429), ("AI_INVALID_OUTPUT", 502)])
def test_ai_failure_uses_existing_http_error_contract(client, auth_headers, monkeypatch, code, status):
    from app.ai_planner import dependencies
    from app.ai_planner.errors import AIInvalidOutputError, AIRateLimitedError, AITimeoutError

    errors = {error.code: error for error in (AIInvalidOutputError, AIRateLimitedError, AITimeoutError)}

    class Provider:
        def __init__(self, before_send, observation=None):
            self.before_send = before_send

        def generate_plan(self, request):
            self.before_send()
            raise errors[code]()

    monkeypatch.setattr(dependencies, "build_ai_planner_provider", lambda **kwargs: Provider(**kwargs))
    response = client.post("/ai-planner/generate-plan", headers=auth_headers, json={"user_prompt": "Hi"})
    assert response.status_code == status
    assert response.json() == {"code": code, "message": errors[code].default_message, "details": {}}
