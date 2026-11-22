"""Production configuration and failure boundaries, without touching live data."""

import pytest
import json
import logging
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app import main


def production_settings(**changes):
    values = {
        "app_env": "production", "jwt_secret": "a-random-test-secret-with-more-than-32-characters",
        "frontend_url": "https://app.example.com", "_env_file": None,
    }
    return Settings(**{**values, **changes})


@pytest.mark.parametrize("secret", ["", "test-secret-key", "your_jwt_secret"])
def test_production_rejects_weak_secret_before_startup(secret):
    with pytest.raises(ValidationError):
        production_settings(jwt_secret=secret)


@pytest.mark.parametrize("origin", [None, "http://app.example.com", "https://*.example.com",
                                   "https://app.example.com/path", "https://user:pass@app.example.com",
                                   "https://app.example.com:bad", "https://bad host.example.com"])
def test_production_requires_one_https_browser_origin(origin):
    with pytest.raises(ValidationError):
        production_settings(frontend_url=origin)


def test_database_outage_preserves_liveness_and_safe_readiness(client, monkeypatch):
    def unavailable():
        raise OperationalError("SECRET SQL", {"password": "SECRET"}, Exception("SECRET database address"))
    monkeypatch.setattr(main, "db_ping", unavailable)
    assert client.get("/health").json() == {"status": "ok"}
    response = client.get("/db-health")
    assert response.status_code == 503
    assert response.json() == {"db": "unavailable"}
    assert "SECRET" not in response.text


def test_migration_failure_never_starts_api(monkeypatch):
    from app import deployment
    monkeypatch.setattr(deployment, "dictConfig", lambda config: None)
    monkeypatch.setattr(deployment, "get_settings", production_settings)
    def migration_failure(*args):
        raise RuntimeError("Migration failed")
    monkeypatch.setattr(deployment.command, "upgrade", migration_failure)
    monkeypatch.setattr(deployment.uvicorn, "run", lambda *args, **kwargs: pytest.fail("API started after failed migration"))
    with pytest.raises(SystemExit) as caught:
        deployment.main()
    assert caught.value.code == 1


def test_production_starts_exactly_one_worker_after_migration(monkeypatch):
    from app import deployment
    monkeypatch.setenv("WEB_CONCURRENCY", "4")
    monkeypatch.setenv("FORWARDED_ALLOW_IPS", "172.20.0.1")
    monkeypatch.setattr(deployment, "dictConfig", lambda config: None)
    monkeypatch.setattr(deployment, "get_settings", production_settings)
    order = []
    monkeypatch.setattr(deployment.command, "upgrade", lambda config, revision: order.append(revision))
    def server(application, **options):
        assert order == ["head"]
        assert application == "app.main:app"
        assert options["workers"] == 1 and options["reload"] is False
        assert options["access_log"] is False
        assert options["forwarded_allow_ips"] == "172.20.0.1"
    monkeypatch.setattr(deployment.uvicorn, "run", server)
    deployment.main()


def test_production_rejects_wildcard_proxy_trust_before_migration(monkeypatch):
    from app import deployment
    monkeypatch.setenv("FORWARDED_ALLOW_IPS", "*")
    monkeypatch.setattr(deployment, "dictConfig", lambda config: None)
    monkeypatch.setattr(deployment, "get_settings", production_settings)
    monkeypatch.setattr(deployment.command, "upgrade", lambda *args: pytest.fail("Must reject proxy config first"))
    with pytest.raises(SystemExit):
        deployment.main()


def test_production_logs_omit_exception_text_sql_and_dependency_payloads():
    from app.core.logging import SafeJsonFormatter
    formatter = SafeJsonFormatter()
    try:
        raise RuntimeError("SECRET SQL password prompt")
    except RuntimeError:
        import sys
        record = logging.LogRecord("app.scheduler", logging.ERROR, "", 0,
                                   "scheduler_generation_failed", (), sys.exc_info())
    record.request_id = "safe-request-id"
    record.outcome = "failure"
    result = formatter.format(record)
    assert "SECRET" not in result
    assert json.loads(result)["error_type"] == "RuntimeError"
    assert json.loads(result)["outcome"] == "failure"
    external = logging.LogRecord("httpx", logging.INFO, "", 0, "GET https://provider/?key=SECRET", (), None)
    assert "SECRET" not in formatter.format(external)


def test_production_cors_has_only_configured_origin_and_settings_repr_hides_db():
    settings = production_settings(frontend_url="https://app.example.com/")
    assert settings.cors_origins == ["https://app.example.com"]
    assert "postgresql://" not in repr(settings)


def test_configuration_preflight_never_migrates_or_starts_server(monkeypatch):
    from app import deployment
    monkeypatch.setattr(deployment, "dictConfig", lambda config: None)
    monkeypatch.setattr(deployment, "get_settings", production_settings)
    monkeypatch.setattr(deployment.command, "upgrade", lambda *args: pytest.fail("Preflight must not migrate"))
    monkeypatch.setattr(deployment.uvicorn, "run", lambda *args, **kwargs: pytest.fail("Preflight must not serve"))
    deployment.main(check_only=True)


def test_invalid_scheduler_timezone_fails_preflight_before_downtime(monkeypatch):
    from app import deployment
    monkeypatch.setattr(deployment, "dictConfig", lambda config: None)
    monkeypatch.setattr(deployment, "get_settings", lambda: production_settings(timezone="Invalid/Zone"))
    monkeypatch.setattr(deployment.command, "upgrade", lambda *args: pytest.fail("Invalid timezone must not migrate"))
    monkeypatch.setattr(deployment.uvicorn, "run", lambda *args, **kwargs: pytest.fail("Invalid timezone must not serve"))
    with pytest.raises(SystemExit) as caught:
        deployment.main(check_only=True)
    assert caught.value.code == 1
