from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import AnyHttpUrl, Field, SecretStr, TypeAdapter, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):

    app_env: Literal["development", "production"] = "development"
    database_url: str = Field(repr=False)

    jwt_secret: SecretStr
    jwt_alg: str = "HS256"
    access_token_expire_minutes: int = 60

    frontend_url: str | None = None

    timezone: str = "Asia/Kuala_Lumpur"
    scheduler_enabled: bool = True

    login_requests_per_minute: int = Field(default=10, gt=0)
    signup_requests_per_hour: int = Field(default=10, gt=0)
    ai_requests_per_minute: int = Field(default=3, gt=0)

    ai_provider: str = "gemini"
    ai_daily_request_limit: int = Field(default=10, gt=0)
    ai_price_profiles: str | None = None
    ai_api_key: SecretStr | None = None
    ai_model: str | None = None

    @model_validator(mode="after")
    def validate_production(self):
        if self.app_env == "production":
            if len(self.jwt_secret.get_secret_value().strip()) < 32:
                raise ValueError("Production JWT_SECRET must contain at least 32 characters")
            TypeAdapter(AnyHttpUrl).validate_python(self.frontend_url or "")
            origin = urlsplit(self.frontend_url or "")
            if (origin.scheme != "https" or not origin.hostname or "*" in origin.netloc
                    or origin.username or origin.password or origin.path not in ("", "/")
                    or origin.query or origin.fragment):
                raise ValueError("Production FRONTEND_URL must be a single HTTPS origin")
        return self

    @property
    def cors_origins(self) -> list[str]:
        origins = [] if self.app_env == "production" else ["http://localhost:5173", "http://localhost:3000"]
        if self.frontend_url:
            origins.append(self.frontend_url.rstrip("/"))
        return origins

    model_config = SettingsConfigDict(
        env_file = PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        hide_input_in_errors=True,
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()
