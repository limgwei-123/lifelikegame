import pytest
from pydantic import ValidationError

from app.core.config import Settings


VALID_DATABASE_URL = (
    "postgresql://user:password@localhost:5432/lifelikegame"
)
VALID_JWT_SECRET = "test-jwt-secret"


def test_settings_accepts_required_values():
    settings = Settings(
        database_url=VALID_DATABASE_URL,
        jwt_secret=VALID_JWT_SECRET,
        _env_file=None,
    )

    assert settings.database_url == VALID_DATABASE_URL
    assert settings.jwt_secret.get_secret_value() == VALID_JWT_SECRET


def test_settings_uses_expected_defaults():
    settings = Settings(
        database_url=VALID_DATABASE_URL,
        jwt_secret=VALID_JWT_SECRET,
        _env_file=None,
    )

    assert settings.jwt_alg == "HS256"
    assert settings.access_token_expire_minutes == 60
    assert settings.frontend_url is None
    assert settings.timezone == "Asia/Kuala_Lumpur"
    assert settings.scheduler_enabled is True
    assert settings.ai_api_key is None
    assert settings.ai_model is None


def test_settings_rejects_missing_required_values(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_converts_environment_strings(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", VALID_DATABASE_URL)
    monkeypatch.setenv("JWT_SECRET", VALID_JWT_SECRET)
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "90")
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")

    settings = Settings(_env_file=None)

    assert settings.access_token_expire_minutes == 90
    assert settings.scheduler_enabled is False


def test_settings_hides_secrets_from_repr():
    settings = Settings(
        database_url=VALID_DATABASE_URL,
        jwt_secret=VALID_JWT_SECRET,
        ai_api_key="test-ai-api-key",
        _env_file=None,
    )

    settings_repr = repr(settings)

    assert VALID_JWT_SECRET not in settings_repr
    assert "test-ai-api-key" not in settings_repr

def test_settings_reads_frontend_url_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", VALID_DATABASE_URL)
    monkeypatch.setenv("JWT_SECRET", VALID_JWT_SECRET)
    monkeypatch.setenv(
        "FRONTEND_URL",
        "https://app.example.com",
    )

    settings = Settings(_env_file=None)

    assert settings.frontend_url == "https://app.example.com"

def test_settings_reads_timezone_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", VALID_DATABASE_URL)
    monkeypatch.setenv("JWT_SECRET", VALID_JWT_SECRET)
    monkeypatch.setenv("TIMEZONE", "UTC")

    settings = Settings(_env_file=None)

    assert settings.timezone == "UTC"


def test_settings_reads_ai_configuration_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", VALID_DATABASE_URL)
    monkeypatch.setenv("JWT_SECRET", VALID_JWT_SECRET)
    monkeypatch.setenv("AI_API_KEY", "test-ai-api-key")
    monkeypatch.setenv("AI_MODEL", "test-ai-model")

    settings = Settings(_env_file=None)

    assert settings.ai_api_key is not None
    assert (
        settings.ai_api_key.get_secret_value()
        == "test-ai-api-key"
    )
    assert settings.ai_model == "test-ai-model"
