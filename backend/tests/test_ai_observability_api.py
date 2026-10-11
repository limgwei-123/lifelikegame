from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
import json
import logging
from threading import Barrier
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai_planner import dependencies
from app.ai_planner.errors import AIAdmissionUnavailableError, AITimeoutError
from app.ai_planner.observation import CallObservation, safe_observe
from app.ai_planner.providers import gemini
from app.ai_planner.providers.base import PlannerResult
from app.ai_planner.schemas import AiPlannerChatRequest
from app.ai_planner.usage_models import AIDailyUsage
from app.ai_planner.usage_record_models import AIUsageRecord
from app.ai_planner.usage_recorder import AIUsageRecorder
from app.ai_planner.usage_service import AIUsageAdmission, AIUsagePolicy, UsageLimitedAIPlannerService
from app.errors.exception import AppError
from ai_usage_support import ai_user_ids
from test_ai_failures import sdk_transport
from test_ai_observability_sdk import wire_response
from test_ai_usage_service import ai_auth, configure
from test_ai_pricing import profile_data


def rows(db, user_id):
    return list(db.scalars(select(AIUsageRecord).where(AIUsageRecord.user_id == user_id)))


def observed_service(db, user_id, recorder=None):
    gate = AIUsageAdmission(db.get_bind(), AIUsagePolicy(10, ZoneInfo("UTC")), lambda: datetime.now(timezone.utc))
    return UsageLimitedAIPlannerService(user_id, gate, lambda **kwargs: gemini.GeminiPlannerProvider(
        api_key="PRIVATE-KEY", model="test-model", **kwargs,
    ), recorder=recorder or AIUsageRecorder(db.get_bind(), {}), provider_name="gemini", model_name="test-model")


def test_retry_creates_one_detail_row_and_one_quota_charge(client, db, ai_auth, sdk_transport, monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="app.ai_usage")
    configure(monkeypatch)
    sdk_transport[0].extend([503, 503, wire_response(promptTokenCount=10, candidatesTokenCount=2)])
    response = client.post("/ai-planner/generate-plan", headers=ai_auth[0], json={"user_prompt": "PRIVATE PROMPT"})
    assert response.status_code == 200, response.text
    assert response.json()["message"] == "When?"
    details = rows(db, ai_auth[1])
    assert len(details) == 1
    row = details[0]
    assert (row.provider, row.model, row.attempts, row.retry_count, row.outcome) == ("gemini", "test-model", 3, 2, "success")
    assert row.prompt_tokens == 10 and row.output_tokens == 2 and row.total_tokens is None
    assert row.estimated_cost is None
    assert db.scalar(select(AIDailyUsage.request_count).where(AIDailyUsage.user_id == ai_auth[1])) == 1
    assert "PRIVATE" not in caplog.text


@pytest.mark.parametrize("failure,code", [(429, "AI_RATE_LIMITED"),
                                           (wire_response(text="PRIVATE malformed", promptTokenCount=10), "AI_INVALID_OUTPUT")])
def test_provider_errors_preserve_http_contract_and_known_usage(client, db, ai_auth, sdk_transport, monkeypatch, failure, code):
    configure(monkeypatch)
    sdk_transport[0].append(failure)
    response = client.post("/ai-planner/generate-plan", headers=ai_auth[0], json={"user_prompt": "PRIVATE"})
    assert response.json()["code"] == code
    row = rows(db, ai_auth[1])[0]
    assert row.outcome == "error" and row.error_code == code
    assert row.prompt_tokens == (10 if code == "AI_INVALID_OUTPUT" else None)


def test_blocked_or_invalid_requests_have_no_invocation_row(client, db, ai_auth, sdk_transport, monkeypatch):
    settings = configure(monkeypatch, ai_daily_request_limit=1)
    headers, user_id = ai_auth
    assert client.post("/ai-planner/generate-plan", json={"user_prompt": "Hi"}).status_code in (401, 403)
    assert client.post("/ai-planner/generate-plan", headers=headers, json={}).status_code == 422
    settings.ai_api_key = None
    assert client.post("/ai-planner/generate-plan", headers=headers, json={"user_prompt": "Hi"}).status_code == 503
    assert not rows(db, user_id)
    from pydantic import SecretStr
    settings.ai_api_key = SecretStr("test-key")
    service = observed_service(db, user_id)
    with service.admission.admit(user_id):
        response = client.post("/ai-planner/generate-plan", headers=headers, json={"user_prompt": "Hi"})
    assert response.json()["code"] == "AI_REQUEST_IN_PROGRESS"
    assert not rows(db, user_id)
    sdk_transport[0].append(wire_response())
    assert client.post("/ai-planner/generate-plan", headers=headers, json={"user_prompt": "Hi"}).status_code == 200
    assert client.post("/ai-planner/generate-plan", headers=headers, json={"user_prompt": "Hi"}).json()["code"] == "AI_DAILY_LIMIT_EXCEEDED"
    assert len(rows(db, user_id)) == 1 and len(sdk_transport[1]) == 1


@pytest.mark.parametrize("failure_point", ["recorder", "snapshot", "cost", "pricing"])
def test_telemetry_failures_do_not_change_api_success(client, ai_auth, sdk_transport, monkeypatch, failure_point):
    from app.ai_planner import usage_recorder
    configure(monkeypatch)
    sdk_transport[0].append(wire_response())

    def fail(*args, **kwargs):
        raise RuntimeError("PRIVATE telemetry error")

    if failure_point == "recorder":
        monkeypatch.setattr(AIUsageRecorder, "record", fail)
    elif failure_point == "snapshot":
        monkeypatch.setattr(CallObservation, "snapshot", fail)
    elif failure_point == "cost":
        monkeypatch.setattr(usage_recorder, "estimate_cost", fail)
    else:
        monkeypatch.setattr(dependencies, "load_price_profiles", fail)
    response = client.post("/ai-planner/generate-plan", headers=ai_auth[0], json={"user_prompt": "Hi"})
    assert response.status_code == 200, response.text


def test_recording_failure_preserves_original_exception_identity(db, ai_user_ids, monkeypatch):
    error = AITimeoutError()

    class Provider:
        def __init__(self, before_send, observation):
            self.before_send, self.observation = before_send, observation

        def generate_plan(self, request):
            self.before_send()
            safe_observe(self.observation, "begin_dispatch")
            safe_observe(self.observation, "finish")
            raise error

    service = observed_service(db, ai_user_ids[0])
    service.provider_factory = Provider
    monkeypatch.setattr(service.recorder, "record", lambda **kwargs: (_ for _ in ()).throw(ValueError("PRIVATE")))
    with pytest.raises(AITimeoutError) as caught:
        service.generate_plan(AiPlannerChatRequest(user_prompt="Hi"))
    assert caught.value is error
    assert db.scalar(select(AIDailyUsage.request_count).where(AIDailyUsage.user_id == ai_user_ids[0])) == 1


def test_recording_is_after_guard_release_and_observations_are_not_reused(db, ai_user_ids, sdk_transport, monkeypatch):
    service = observed_service(db, ai_user_ids[0])
    sdk_transport[0].append(wire_response())
    seen = []
    original = service.recorder.record

    def record(**kwargs):
        with service.admission.admit(ai_user_ids[0]):
            seen.append(kwargs["observation"])
        original(**kwargs)

    monkeypatch.setattr(service.recorder, "record", record)
    for _ in range(2):
        service.generate_plan(AiPlannerChatRequest(user_prompt="Hi"))
    assert len(seen) == 2 and seen[0] is not seen[1]
    assert len(rows(db, ai_user_ids[0])) == 2


def test_unknown_exception_uses_safe_telemetry_label_but_is_not_replaced(db, ai_user_ids):
    error = RuntimeError("PRIVATE business error")

    class Provider:
        def __init__(self, before_send, observation):
            self.before_send, self.observation = before_send, observation

        def generate_plan(self, request):
            self.before_send()
            self.observation.begin_dispatch()
            self.observation.finish()
            raise error

    service = observed_service(db, ai_user_ids[0])
    service.provider_factory = Provider
    with pytest.raises(RuntimeError) as caught:
        service.generate_plan(AiPlannerChatRequest(user_prompt="Hi"))
    assert caught.value is error
    assert rows(db, ai_user_ids[0])[0].error_code == "AI_INTERNAL_ERROR"


def test_guard_cleanup_error_is_recorded_as_service_error(db, ai_user_ids, sdk_transport, monkeypatch):
    from sqlalchemy.engine import Connection
    service = observed_service(db, ai_user_ids[0])
    sdk_transport[0].append(wire_response(promptTokenCount=5))
    original = Connection.scalar

    def scalar(connection, statement, *args, **kwargs):
        if "pg_advisory_unlock" in str(statement):
            return False
        return original(connection, statement, *args, **kwargs)

    monkeypatch.setattr(Connection, "scalar", scalar)
    with pytest.raises(AIAdmissionUnavailableError):
        service.generate_plan(AiPlannerChatRequest(user_prompt="Hi"))
    row = rows(db, ai_user_ids[0])[0]
    assert row.outcome == "error" and row.error_code == "AI_ADMISSION_UNAVAILABLE"
    assert row.prompt_tokens == 5


def test_malformed_pricing_is_safe_and_never_logged(client, db, ai_auth, sdk_transport, monkeypatch, caplog):
    configure(monkeypatch, ai_price_profiles="PRIVATE malformed config")
    sdk_transport[0].append(wire_response())
    response = client.post("/ai-planner/generate-plan", headers=ai_auth[0], json={"user_prompt": "Hi"})
    assert response.status_code == 200
    assert rows(db, ai_auth[1])[0].cost_status == "unknown"
    assert "PRIVATE" not in caplog.text


def test_concurrent_users_have_independent_observations(db, ai_user_ids):
    barrier = Barrier(2)
    engine = db.get_bind()

    class Provider:
        def __init__(self, before_send, observation):
            self.before_send, self.observation = before_send, observation

        def generate_plan(self, request):
            from app.ai_planner.observation import TokenUsage
            self.before_send()
            self.observation.begin_dispatch()
            barrier.wait(timeout=10)
            self.observation.attempt()
            self.observation.capture_usage(TokenUsage(prompt_tokens=int(request.user_prompt)))
            self.observation.finish()
            return PlannerResult(status="need_more_info", message="When?")

    def worker(user_id, count):
        gate = AIUsageAdmission(engine, AIUsagePolicy(10, ZoneInfo("UTC")), lambda: datetime.now(timezone.utc))
        service = UsageLimitedAIPlannerService(user_id, gate, Provider, recorder=AIUsageRecorder(engine, {}),
                                              provider_name="gemini", model_name="test-model")
        return service.generate_plan(AiPlannerChatRequest(user_prompt=str(count)))

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, user_id, count) for user_id, count in zip(ai_user_ids, (5, 9))]
        for future in futures:
            assert future.result(timeout=15).message == "When?"
    assert rows(db, ai_user_ids[0])[0].prompt_tokens == 5
    assert rows(db, ai_user_ids[1])[0].prompt_tokens == 9


@pytest.mark.parametrize("existing", ["existing-request", "PRIVATE\ninvalid"])
def test_correlation_id_is_reused_or_safely_replaced(db, ai_user_ids, sdk_transport, existing):
    from app.core.behaviors import bind_request_id, reset_request_id
    sdk_transport[0].append(wire_response())
    token = bind_request_id(existing)
    try:
        observed_service(db, ai_user_ids[0]).generate_plan(AiPlannerChatRequest(user_prompt="Hi"))
    finally:
        reset_request_id(token)
    row = rows(db, ai_user_ids[0])[0]
    assert row.request_id == existing if existing == "existing-request" else "PRIVATE" not in row.request_id


@pytest.mark.parametrize("attempts,status", [(1, "estimated"), (3, "partial")])
def test_configured_cost_and_completeness_are_persisted_end_to_end(client, db, ai_auth, sdk_transport, monkeypatch, attempts, status):
    data = profile_data()
    data["model"] = "test-model"
    configure(monkeypatch, ai_price_profiles=json.dumps([data]))
    sdk_transport[0].extend([503] * (attempts - 1) + [wire_response(
        promptTokenCount=1000, cachedContentTokenCount=200, candidatesTokenCount=100,
        thoughtsTokenCount=50, toolUsePromptTokenCount=0, totalTokenCount=1150,
    )])
    response = client.post("/ai-planner/generate-plan", headers=ai_auth[0], json={"user_prompt": "Hi"})
    assert response.status_code == 200
    row = rows(db, ai_auth[1])[0]
    assert row.estimated_cost == Decimal("0.001200000000")
    assert (row.currency, row.price_version, row.cost_status) == ("USD", "v1", status)


def test_provider_latency_excludes_quota_and_recording_time(db, ai_user_ids, sdk_transport, monkeypatch):
    from app.ai_planner import usage_service
    from app.ai_planner.usage_repository import AIUsageRepository
    ticks = [10.0]
    observation_factory = CallObservation
    monkeypatch.setattr(usage_service, "CallObservation", lambda: observation_factory(timer=lambda: ticks[0]))
    consume = AIUsageRepository.try_consume

    def delayed_consume(*args, **kwargs):
        ticks[0] += 100
        return consume(*args, **kwargs)

    monkeypatch.setattr(AIUsageRepository, "try_consume", delayed_consume)
    client_factory = gemini.genai.Client

    def client(**kwargs):
        def request_hook(request):
            ticks[0] += 2
        kwargs["http_options"].client_args["event_hooks"]["request"].append(request_hook)
        return client_factory(**kwargs)

    monkeypatch.setattr(gemini.genai, "Client", client)
    sdk_transport[0].append(wire_response())
    service = observed_service(db, ai_user_ids[0])
    record = service.recorder.record

    def delayed_record(**kwargs):
        ticks[0] += 1000
        record(**kwargs)

    monkeypatch.setattr(service.recorder, "record", delayed_record)
    service.generate_plan(AiPlannerChatRequest(user_prompt="Hi"))
    assert rows(db, ai_user_ids[0])[0].latency_ms == Decimal("2000.000")
