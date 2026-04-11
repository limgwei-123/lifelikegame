from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_user
from app.workflows.dependencies import get_workflow_service
from app.workflows.interfaces import WorkflowServiceInterface
from app.workflows.schemas import (
    CreateTaskWithScheduleRequest,
    TaskWithScheduleResponse,
)

router = APIRouter(prefix="/workflows", tags=["workflows"])

@router.post(
    "/goals/{goal_id}/tasks",
    response_model=TaskWithScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_task_with_schedule(
    goal_id: int,
    payload: CreateTaskWithScheduleRequest,
    current_user=Depends(get_current_user),
    workflow_service: WorkflowServiceInterface = Depends(get_workflow_service),
):
    return workflow_service.create_task_with_schedule(
        goal_id=goal_id,
        user_id=current_user.id,
        payload=payload,
    )