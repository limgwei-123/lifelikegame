from fastapi import APIRouter, Depends, status
from app.ai_planner.schemas import AiPlannerChatRequest, AiPlannerResponse
from app.ai_planner.dependencies import get_limited_ai_planner_service, get_ai_draft_engine, get_ai_draft_service, build_ai_draft_service
from app.ai_planner.draft_schemas import DraftPlan, DraftResponse
from app.ai_planner.draft_service import AIPlanDraftService
from app.ai_planner.providers.base import GeneratedPlan
from app.core.unit_of_work import build_unit_of_work
from sqlalchemy import Engine
from sqlalchemy.orm import Session
from uuid import UUID
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
    ai_planner_service: AIPlannerServiceInterface = Depends(get_limited_ai_planner_service),
    draft_engine: Engine = Depends(get_ai_draft_engine),
):
    response = ai_planner_service.generate_plan(payload)
    if response.status == "plan_ready":
        # Only the short draft write owns this Session, after the AI guard is released.
        with Session(draft_engine) as db, build_unit_of_work(db).begin():
            saved = build_ai_draft_service(db).save_generated(user_id=current_user.id, plan=response.plan)
        return response.model_copy(update={
            "draft_id": saved.draft_id,
            "plan": GeneratedPlan.model_validate(saved.plan.model_dump()),
        })
    return response


@router.post("/drafts/{draft_id}/revisions", response_model=DraftResponse, status_code=status.HTTP_201_CREATED)
def revise_draft(
    draft_id: UUID,
    payload: DraftPlan,
    current_user=Depends(get_current_user),
    draft_service: AIPlanDraftService = Depends(get_ai_draft_service),
):
    return draft_service.revise(user_id=current_user.id, draft_id=draft_id, plan=payload)
