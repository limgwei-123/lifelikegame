from app.ai_planner.service import AIPlannerService
from app.ai_planner.interfaces import AIPlannerServiceInterface


def get_ai_planner_service() -> AIPlannerServiceInterface:
    return AIPlannerService()