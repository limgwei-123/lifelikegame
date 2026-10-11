import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai_planner import dependencies
from app.ai_planner.errors import AIQuotaExceededError
from app.ai_planner.providers import gemini
from app.ai_planner.providers.base import PlannerRequest
from app.ai_planner.schemas import AiPlannerChatRequest
from app.ai_planner.usage_models import AIDailyUsage
from app.ai_planner.usage_service import AIUsageAdmission, AIUsagePolicy
from app.core.config import Settings
from app.errors.exception import AppError
from app.users.models import User
from ai_usage_support import ai_user_ids
from test_ai_failures import sdk_transport


SUCCESS = json.dumps({"status": "need_more_info", "message": "When?"})


def limited_service(db, user_id, limit=10):
    from app.ai_planner.usage_service import UsageLimitedAIPlannerService

    gate = AIUsageAdmission(db.get_bind(), AIUsagePolicy(limit, ZoneInfo("Asia/Kuala_Lumpur")),
                            lambda: datetime(2026, 10, 11, 12, tzinfo=timezone.utc))
    return UsageLimitedAIPlannerService(user_id, gate, lambda **kwargs: gemini.GeminiPlannerProvider(
        api_key="test-key", model="test-model", **kwargs,
    ))


@pytest.mark.parametrize("outcome,code,attempts", [
    (SUCCESS, None, 1),
    (httpx.ReadTimeout("private"), "AI_TIMEOUT", 3),
    (429, "AI_RATE_LIMITED", 3),
    (503, "AI_UNAVAILABLE", 3),
    ("invalid JSON", "AI_INVALID_OUTPUT", 1),
])
def test_sdk_attempts_count_one_logical_request(db, ai_user_ids, sdk_transport, outcome, code, attempts):
    outcomes, calls, clients = sdk_transport
    outcomes.append(outcome)
    service = limited_service(db, ai_user_ids[0], limit=1)
    payload = AiPlannerChatRequest(user_prompt="Hi")
    if code:
        with pytest.raises(AppError) as error:
            service.generate_plan(payload)
        assert error.value.code == code
    else:
        assert service.generate_plan(payload).message == "When?"
    assert len(calls) == attempts
    assert db.scalar(select(AIDailyUsage.request_count).where(AIDailyUsage.user_id == ai_user_ids[0])) == 1
    with pytest.raises(AIQuotaExceededError):
        service.generate_plan(payload)
    assert len(calls) == attempts
    assert all(client._api_client._httpx_client.is_closed for client in clients)


def test_quota_does_not_commit_or_rollback_unrelated_request_session(db, ai_user_ids, sdk_transport):
    sdk_transport[0].append(SUCCESS)
    other = db.get(User, ai_user_ids[1])
    original = other.email
    other.email = f"pending-{uuid4()}@example.com"
    db.flush()
    limited_service(db, ai_user_ids[0]).generate_plan(AiPlannerChatRequest(user_prompt="Hi"))
    with Session(db.get_bind()) as observer:
        assert observer.get(User, ai_user_ids[1]).email == original
        assert observer.scalar(select(AIDailyUsage.request_count).where(AIDailyUsage.user_id == ai_user_ids[0])) == 1
    assert other.email != original
    db.rollback()
    assert db.get(User, ai_user_ids[1]).email == original


def test_two_sdk_retries_then_success_still_consume_one(db, ai_user_ids, sdk_transport):
    sdk_transport[0].extend([503, 503, SUCCESS])
    response = limited_service(db, ai_user_ids[0]).generate_plan(AiPlannerChatRequest(user_prompt="Hi"))
    assert response.message == "When?"
    assert len(sdk_transport[1]) == 3
    assert db.scalar(select(AIDailyUsage.request_count).where(AIDailyUsage.user_id == ai_user_ids[0])) == 1


def authenticate(client):
    credentials = {"email": f"quota-{uuid4()}@example.com", "password": "password123"}
    assert client.post("/auth/signup", json=credentials).status_code in (200, 201)
    token = client.post("/auth/login", json=credentials).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_id = UUID(client.get("/users/me", headers=headers).json()["id"])
    return headers, user_id


@pytest.fixture
def ai_auth(client):
    return authenticate(client)


def configure(monkeypatch, **kwargs):
    settings = Settings(_env_file=None, ai_api_key="test-key", ai_model="test-model", **kwargs)
    monkeypatch.setattr(dependencies, "get_settings", lambda: settings)
    return settings


def test_http_ten_requests_then_quota_error_with_reset(client, db, ai_auth, sdk_transport, monkeypatch):
    configure(monkeypatch)
    sdk_transport[0].append(SUCCESS)
    headers, user_id = ai_auth
    for _ in range(10):
        response = client.post("/ai-planner/generate-plan", headers=headers, json={"user_prompt": "Hi"})
        assert response.status_code == 200, response.text
    response = client.post("/ai-planner/generate-plan", headers=headers, json={"user_prompt": "Hi"})
    assert response.status_code == 429
    assert response.json()["code"] == "AI_DAILY_LIMIT_EXCEEDED"
    assert datetime.fromisoformat(response.json()["details"]["reset_at"]).utcoffset().total_seconds() == 0
    assert len(sdk_transport[1]) == 10
    assert db.scalar(select(AIDailyUsage.request_count).where(AIDailyUsage.user_id == user_id)) == 10
    other_headers, other_id = authenticate(client)
    response = client.post("/ai-planner/generate-plan", headers=other_headers, json={"user_prompt": "Hi"})
    assert response.status_code == 200
    assert db.scalar(select(AIDailyUsage.request_count).where(AIDailyUsage.user_id == other_id)) == 1


@pytest.mark.parametrize("configuration", ["missing_key", "unsupported"])
def test_http_local_configuration_failure_does_not_charge(client, db, ai_auth, sdk_transport, monkeypatch, configuration):
    settings = configure(monkeypatch)
    if configuration == "missing_key":
        settings.ai_api_key = None
    else:
        settings.ai_provider = "unsupported"
    headers, user_id = ai_auth
    response = client.post("/ai-planner/generate-plan", headers=headers, json={"user_prompt": "Hi"})
    assert response.status_code == 503
    assert response.json()["code"] == "AI_CONFIGURATION_ERROR"
    assert not sdk_transport[1]
    assert db.scalar(select(AIDailyUsage).where(AIDailyUsage.user_id == user_id)) is None


def test_http_auth_and_validation_do_not_charge(client, db, ai_auth, sdk_transport, monkeypatch):
    configure(monkeypatch)
    headers, user_id = ai_auth
    response = client.post("/ai-planner/generate-plan", json={"user_prompt": "Hi"})
    assert response.status_code in (401, 403)
    response = client.post("/ai-planner/generate-plan", headers=headers, json={})
    assert response.status_code == 422
    assert not sdk_transport[1]
    assert db.scalar(select(AIDailyUsage).where(AIDailyUsage.user_id == user_id)) is None


def test_http_inflight_request_returns_distinct_error(client, db, ai_auth, sdk_transport, monkeypatch):
    configure(monkeypatch)
    headers, user_id = ai_auth
    gate = AIUsageAdmission(db.get_bind(), AIUsagePolicy(10, ZoneInfo("UTC")), lambda: datetime.now(timezone.utc))
    with gate.admit(user_id):
        response = client.post("/ai-planner/generate-plan", headers=headers, json={"user_prompt": "Hi"})
    assert response.status_code == 429
    assert response.json()["code"] == "AI_REQUEST_IN_PROGRESS"
    assert not sdk_transport[1]


def test_invalid_timezone_is_configuration_error_before_admission(client, ai_auth, sdk_transport, monkeypatch):
    configure(monkeypatch, timezone="Invalid/SystemZone")
    monkeypatch.setattr(AIUsageAdmission, "admit", lambda *args: pytest.fail("Must validate timezone first"))
    response = client.post("/ai-planner/generate-plan", headers=ai_auth[0], json={"user_prompt": "Hi"})
    assert response.status_code == 503
    assert response.json()["code"] == "AI_CONFIGURATION_ERROR"
    assert not sdk_transport[1]


def test_http_database_failure_never_dispatches(client, ai_auth, sdk_transport, monkeypatch):
    from sqlalchemy.exc import OperationalError
    from app.ai_planner.usage_repository import AIUsageRepository

    configure(monkeypatch)

    def fail(*args, **kwargs):
        raise OperationalError("private SQL", {}, Exception("private database details"))

    monkeypatch.setattr(AIUsageRepository, "try_consume", fail)
    response = client.post("/ai-planner/generate-plan", headers=ai_auth[0], json={"user_prompt": "Hi"})
    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "AI_ADMISSION_UNAVAILABLE"
    assert body["details"] == {}
    assert "private" not in response.text
    assert not sdk_transport[1]


@pytest.mark.parametrize("stage", ["prompt", "client", "config"])
def test_sdk_preparation_failure_never_charges(monkeypatch, stage):
    generate, close, charge = Mock(), Mock(), Mock()
    monkeypatch.setattr(gemini.genai, "Client", lambda **kwargs: SimpleNamespace(
        models=SimpleNamespace(generate_content=generate), close=close,
    ))
    fail = Mock(side_effect=ValueError("local preparation"))
    if stage == "prompt":
        monkeypatch.setattr(gemini, "build_generate_plan_prompt", fail)
    elif stage == "client":
        monkeypatch.setattr(gemini.genai, "Client", fail)
    else:
        monkeypatch.setattr(gemini.types, "GenerateContentConfig", fail)
    with pytest.raises(ValueError, match="local preparation"):
        gemini.GeminiPlannerProvider(api_key="test", model="test", before_send=charge).generate_plan(
            PlannerRequest(user_prompt="Hi", conversation_history=[]),
        )
    charge.assert_not_called()
    generate.assert_not_called()
    assert close.call_count == (1 if stage == "config" else 0)


@pytest.mark.parametrize("error", [AIQuotaExceededError(datetime.now(timezone.utc)), ValueError("local hook")])
def test_hook_failure_is_not_converted_to_vendor_error_and_closes_client(monkeypatch, error):
    generate, close = Mock(), Mock()
    monkeypatch.setattr(gemini.genai, "Client", lambda **kwargs: SimpleNamespace(
        models=SimpleNamespace(generate_content=generate), close=close,
    ))
    with pytest.raises(type(error)) as caught:
        gemini.GeminiPlannerProvider(api_key="test", model="test", before_send=Mock(side_effect=error)).generate_plan(
            PlannerRequest(user_prompt="Hi", conversation_history=[]),
        )
    assert caught.value is error
    generate.assert_not_called()
    close.assert_called_once()
