from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):

    database_url: str

    jwt_secret: SecretStr
    jwt_alg: str = "HS256"
    access_token_expire_minutes: int = 60

    frontend_url: str | None = None

    timezone: str = "Asia/Kuala_Lumpur"
    scheduler_enabled: bool = True

    ai_api_key: SecretStr | None = None
    ai_model: str | None = None

    model_config = SettingsConfigDict(
        env_file = PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()