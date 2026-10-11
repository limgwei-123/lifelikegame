from datetime import datetime, timezone
import logging
from typing import Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Depends
from sqlalchemy.orm import Session

from app.ai_planner.errors import AIConfigurationError
from app.ai_planner.observation import CallObservation, safe_log
from app.ai_planner.pricing import load_price_profiles
from app.ai_planner.usage_recorder import AIUsageRecorder
from app.ai_planner.service import AIPlannerService
from app.ai_planner.interfaces import AIPlannerServiceInterface
from app.ai_planner.providers.base import AIPlannerProvider
from app.core.config import get_settings
from app.ai_planner.usage_service import AIUsageAdmission, AIUsagePolicy, UsageLimitedAIPlannerService
from app.auth.dependencies import get_current_user
from app.db import get_session
from app.db import get_db
from app.ai_planner.draft_repository import AIPlanDraftRepository
from app.ai_planner.draft_service import AIPlanDraftService
from app.scoring_schemes.dependencies import build_scoring_scheme_service
from app.users.models import User


def build_ai_draft_service(db: Session) -> AIPlanDraftService:
    return AIPlanDraftService(AIPlanDraftRepository(db), build_scoring_scheme_service(db))


def get_ai_draft_service(db: Session = Depends(get_db, scope="function")) -> AIPlanDraftService:
    return build_ai_draft_service(db)


def get_ai_draft_engine(db: Session = Depends(get_session)):
    return db.get_bind().engine


def build_ai_planner_provider(*, before_send: Callable[[], None] | None = None,
                              observation: CallObservation | None = None) -> AIPlannerProvider:
    settings = get_settings()
    if settings.ai_provider != "gemini":
        raise AIConfigurationError()

    from app.ai_planner.providers.gemini import GeminiPlannerProvider

    return GeminiPlannerProvider(
        api_key=settings.ai_api_key.get_secret_value() if settings.ai_api_key is not None else None,
        model=settings.ai_model,
        before_send=before_send,
        observation=observation,
    )


def build_ai_planner_service() -> AIPlannerServiceInterface:
    return AIPlannerService(build_ai_planner_provider())


def get_ai_planner_service() -> AIPlannerServiceInterface:
    return build_ai_planner_service()


def get_limited_ai_planner_service(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> AIPlannerServiceInterface:
    settings = get_settings()
    try:
        policy = AIUsagePolicy(settings.ai_daily_request_limit, ZoneInfo(settings.timezone))
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise AIConfigurationError() from exc
    admission = AIUsageAdmission(
        db.get_bind().engine,
        policy,
        lambda: datetime.now(timezone.utc),
    )
    recorder = None
    try:
        try:
            profiles = load_price_profiles(settings.ai_price_profiles)
        except Exception:
            profiles = {}
            safe_log(logging.getLogger("app.ai_usage"), "warning", "ai_pricing_configuration_invalid")
        recorder = AIUsageRecorder(db.get_bind().engine, profiles)
    except Exception:
        safe_log(logging.getLogger("app.ai_usage"), "warning", "ai_observation_failed")
    return UsageLimitedAIPlannerService(
        current_user.id, admission, build_ai_planner_provider,
        recorder=recorder, provider_name=settings.ai_provider, model_name=settings.ai_model,
    )
