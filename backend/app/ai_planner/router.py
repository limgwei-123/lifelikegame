from fastapi import APIRouter, Depends, status
from app.ai_planner.schemas import AiPlannerChatRequest, AiPlannerResponse
from app.ai_planner.dependencies import get_ai_planner_service
from app.ai_planner.interfaces import AIPlannerServiceInterface
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/ai-planner", tags=["AI Planner"])


@router.post(
    "/generate-plan",
    response_model=AiPlannerResponse,
    status_code=status.HTTP_200_OK,
)
def generate_plan(
    payload: AiPlannerChatRequest,
    current_user = Depends(get_current_user),
    ai_planner_service: AIPlannerServiceInterface = Depends(get_ai_planner_service),
):
    return ai_planner_service.generate_plan(payload)