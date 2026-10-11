from app.ai_planner.service import AIPlannerService
from app.ai_planner.interfaces import AIPlannerServiceInterface
from app.ai_planner.providers.base import AIPlannerProvider
from app.core.config import get_settings


def build_ai_planner_provider() -> AIPlannerProvider:
    settings = get_settings()
    if settings.ai_provider != "gemini":
        raise ValueError("Unsupported AI_PROVIDER; supported provider: gemini")

    from app.ai_planner.providers.gemini import GeminiPlannerProvider

    return GeminiPlannerProvider(
        api_key=settings.ai_api_key.get_secret_value() if settings.ai_api_key is not None else None,
        model=settings.ai_model,
    )


def build_ai_planner_service() -> AIPlannerServiceInterface:
    return AIPlannerService(build_ai_planner_provider())


def get_ai_planner_service() -> AIPlannerServiceInterface:
    return build_ai_planner_service()
