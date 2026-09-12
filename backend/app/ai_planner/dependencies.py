from app.ai_planner.service import AIPlannerService
from app.ai_planner.interfaces import AIPlannerServiceInterface


def build_ai_planner_service() -> AIPlannerServiceInterface:
    return AIPlannerService()


def get_ai_planner_service() -> AIPlannerServiceInterface:
    return build_ai_planner_service()
