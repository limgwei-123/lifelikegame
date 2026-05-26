from typing import Any, Literal, TypedDict

from app.ai_planner.schemas import AiPlannerChatRequest, AiPlannerResponse


AiPlannerStatus = Literal["need_more_info", "plan_ready"]


class AiPlannerGraphState(TypedDict, total=False):
    payload: AiPlannerChatRequest

    raw_result: str
    data: dict[str, Any]

    status: AiPlannerStatus
    message: str
    questions: list[str]
    plan: dict[str, Any] | None

    ai_response: AiPlannerResponse