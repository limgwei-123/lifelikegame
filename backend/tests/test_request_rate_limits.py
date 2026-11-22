"""HTTP regressions for the real auth and paid-AI admission boundaries."""

from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from limits import RateLimitItemPerMinute
from pydantic import SecretStr, ValidationError

from sqlalchemy import select

from app.ai_planner.usage_models import AIDailyUsage
from app.ai_planner.usage_record_models import AIUsageRecord
from app.core.config import Settings, get_settings
from app.core.rate_limiting import RequestRateLimiter, RequestRateLimitedError
from app.main import app
from app.users.models import User
from test_ai_failures import sdk_transport


def test_login_blocks_after_ten_attempts_even_with_different_forwarded_ips(client):
    payload = {"email": f"unknown-{uuid4()}@example.com", "password": "password123"}
    for _ in range(10):
        assert client.post("/auth/login", json=payload).status_code == 401
    response = client.post("/auth/login", json=payload, headers={
        "X-Forwarded-For": "203.0.113.25", "Forwarded": "for=203.0.113.26",
    })
    assert response.status_code == 429
    assert response.json()["code"] == "REQUEST_RATE_LIMITED"
    assert 1 <= int(response.headers["Retry-After"]) <= 60


def test_signup_counts_duplicates_and_does_not_create_blocked_account(client, db):
    payload = {"email": f"signup-limit-{uuid4()}@example.com", "password": "password123"}
    blocked_email = f"blocked-{uuid4()}@example.com"
    try:
        assert client.post("/auth/signup", json=payload).status_code == 201
        for _ in range(9):
            assert client.post("/auth/signup", json=payload).status_code == 409
        response = client.post("/auth/signup", json={**payload, "email": blocked_email})
        assert response.status_code == 429
        assert 1 <= int(response.headers["Retry-After"]) <= 3600
        assert db.scalar(select(User).where(User.email == blocked_email)) is None
    finally:
        db.rollback()
        db.query(User).filter(User.email.in_([payload["email"], blocked_email])).delete()
        db.commit()


def test_ai_burst_rejection_does_not_dispatch_or_charge_and_other_user_can_run(
    client, db, ownership_case, sdk_transport, monkeypatch,
):
    # Keep provider configuration valid without using any external network.
    monkeypatch.setattr(get_settings(), "ai_api_key", SecretStr("test-key"))
    monkeypatch.setattr(get_settings(), "ai_model", "test-model")
    sdk_transport[0].append('{"status":"need_more_info","message":"When?"}')
    payload = {"user_prompt": "Hi"}
    owner = ownership_case["owner"]
    for _ in range(4):
        assert client.post("/ai-planner/generate-plan", json=payload).status_code in (401, 403)
    for _ in range(3):
        assert client.post("/ai-planner/generate-plan", headers=owner["headers"], json=payload).status_code == 200
    response = client.post("/ai-planner/generate-plan", headers=owner["headers"], json=payload)
    assert response.status_code == 429
    assert response.json()["code"] == "REQUEST_RATE_LIMITED"
    assert len(sdk_transport[1]) == 3
    assert len(list(db.scalars(select(AIUsageRecord).where(AIUsageRecord.user_id == owner["user"].id)))) == 3
    db.expire_all()
    assert db.scalar(select(AIDailyUsage.request_count).where(AIDailyUsage.user_id == owner["user"].id)) == 3
    response = client.post("/ai-planner/generate-plan", headers=ownership_case["other"]["headers"], json=payload)
    assert response.status_code == 200
    assert len(sdk_transport[1]) == 4


def test_configured_ai_burst_recovers_and_keeps_daily_charge_count(
    client, db, ownership_case, sdk_transport, monkeypatch, rate_clock,
):
    monkeypatch.setattr(get_settings(), "ai_requests_per_minute", 1)
    monkeypatch.setattr(get_settings(), "ai_api_key", SecretStr("test-key"))
    monkeypatch.setattr(get_settings(), "ai_model", "test-model")
    app.state.request_limiter = RequestRateLimiter(clock=lambda: rate_clock.now)
    sdk_transport[0].append('{"status":"need_more_info","message":"When?"}')
    owner = ownership_case["owner"]
    payload = {"user_prompt": "Hi"}
    assert client.post("/ai-planner/generate-plan", headers=owner["headers"], json=payload).status_code == 200
    headers = {**owner["headers"], "Origin": "http://localhost:5173"}
    response = client.post("/ai-planner/generate-plan", headers=headers, json=payload)
    assert response.status_code == 429
    assert "retry-after" in response.headers["Access-Control-Expose-Headers"].lower()
    assert response.headers["Retry-After"] == "60"
    rate_clock.now += 60
    assert client.post("/ai-planner/generate-plan", headers=headers, json=payload).status_code == 200
    assert len(sdk_transport[1]) == 2
    db.expire_all()
    assert db.scalar(select(AIDailyUsage.request_count).where(AIDailyUsage.user_id == owner["user"].id)) == 2


@pytest.fixture
def rate_clock(monkeypatch):
    # Replace only the limiter/library clocks, leaving logs, JWT and DB time real.
    import limits.storage.memory as memory
    import limits.strategies as strategies
    clock = SimpleNamespace(now=1000000.0)
    fake_time = SimpleNamespace(time=lambda: clock.now)
    monkeypatch.setattr(memory, "time", fake_time)
    monkeypatch.setattr(strategies, "time", fake_time)
    return clock


def test_login_window_recovers_without_blocked_attempts_extending_it(client, monkeypatch, rate_clock):
    app.state.request_limiter = RequestRateLimiter(clock=lambda: rate_clock.now)
    monkeypatch.setattr(get_settings(), "login_requests_per_minute", 1)
    payload = {"email": "not-registered@example.com", "password": "password123"}
    assert client.post("/auth/login", json=payload).status_code == 401
    rate_clock.now += 59
    denied = client.post("/auth/login", json=payload)
    assert denied.status_code == 429
    assert denied.headers["Retry-After"] == "1"
    assert denied.json()["details"] == {"retry_after": 1}
    rate_clock.now += 1
    assert client.post("/auth/login", json=payload).status_code == 401


def test_ip_and_endpoint_limits_are_independent(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "login_requests_per_minute", 1)
    payload = {"email": "not-registered@example.com", "password": "password123"}
    assert client.post("/auth/login", json=payload).status_code == 401
    assert client.post("/auth/login", json=payload).status_code == 429
    # Deliberately don't enter a second lifespan: both clients share one process.
    other = TestClient(app, client=("203.0.113.50", 50000))
    try:
        assert other.post("/auth/login", json=payload).status_code == 401
        assert other.post("/auth/login", json=payload).status_code == 429
        assert client.post("/auth/login", json=payload).status_code == 429
        assert client.get("/health").status_code == 200
        # Signup has its own counter and still runs normal payload validation.
        assert client.post("/auth/signup", json={}).status_code == 422
    finally:
        other.close()


def test_successful_login_counts_and_rejected_login_skips_password_work(client, test_user, monkeypatch):
    monkeypatch.setattr(get_settings(), "login_requests_per_minute", 1)
    assert client.post("/auth/login", json=test_user).status_code == 200
    import app.auth.service as auth_service
    monkeypatch.setattr(auth_service, "verify_password", lambda *args: pytest.fail("Blocked before password verification"))
    assert client.post("/auth/login", json=test_user).status_code == 429


def test_signup_limit_is_configurable_and_rejects_before_hashing(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "signup_requests_per_hour", 1)
    assert client.post("/auth/signup", json={}).status_code == 422
    import app.auth.service as auth_service
    monkeypatch.setattr(auth_service, "hash_password", lambda *args: pytest.fail("Blocked before password hashing"))
    response = client.post("/auth/signup", json={"email": f"blocked-{uuid4()}@example.com", "password": "password123"})
    assert response.status_code == 429


def test_active_identity_cap_preserves_existing_counters_and_recovers(rate_clock):
    limiter = RequestRateLimiter(max_keys=2, clock=lambda: rate_clock.now)
    rule = RateLimitItemPerMinute(2)
    try:
        limiter.check("login", "a", rule)
        limiter.check("login", "b", rule)
        with pytest.raises(RequestRateLimitedError):
            limiter.check("login", "c", rule)
        # Existing identities keep their remaining allowance at capacity.
        limiter.check("login", "a", rule)
        with pytest.raises(RequestRateLimitedError):
            limiter.check("login", "a", rule)
        rate_clock.now += 60
        limiter.check("login", "c", rule)
        limiter.check("login", "d", rule)
        with pytest.raises(RequestRateLimitedError):
            limiter.check("login", "e", rule)
    finally:
        limiter.clear()


def test_concurrent_checks_cannot_exceed_allowance():
    limiter = RequestRateLimiter()
    def attempt(_):
        try:
            limiter.check("login", "one-ip", RateLimitItemPerMinute(3))
            return True
        except RequestRateLimitedError:
            return False
    try:
        with ThreadPoolExecutor(max_workers=12) as workers:
            assert sum(workers.map(attempt, range(20))) == 3
    finally:
        limiter.clear()


@pytest.mark.parametrize("field", ["login_requests_per_minute", "signup_requests_per_hour", "ai_requests_per_minute"])
@pytest.mark.parametrize("value", [0, -1])
def test_invalid_limit_configuration_fails_closed(field, value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: value})


def test_environment_limit_controls_login_admission(client, monkeypatch):
    monkeypatch.setenv("LOGIN_REQUESTS_PER_MINUTE", "1")
    settings = Settings(_env_file=None)
    import app.core.rate_limiting as rate_limiting
    monkeypatch.setattr(rate_limiting, "get_settings", lambda: settings)
    payload = {"email": "not-registered@example.com", "password": "password123"}
    assert client.post("/auth/login", json=payload).status_code == 401
    assert client.post("/auth/login", json=payload).status_code == 429
