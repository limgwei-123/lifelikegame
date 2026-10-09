from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_user
from app.core.mediator import Mediator
from app.task_schedules.dtos import CreateTaskScheduleDTO
from app.tasks.dtos import CreateTaskDTO
from app.workflows.task_workflow.commands import CreateTaskWithScheduleCommand
from app.workflows.task_workflow.dependencies import get_create_task_with_schedule_mediator, get_task_workflow_service
from app.workflows.task_workflow.dtos import CreateTaskWithScheduleDTO
from app.workflows.task_workflow.interfaces import TaskWorkflowServiceInterface

from app.workflows.redemption_workflow.commands import RedeemRewardCommand
from app.workflows.redemption_workflow.dependencies import get_redeem_reward_mediator

from app.workflows.task_workflow.schemas import (
    CreateTaskWithScheduleRequest,
    TaskWithScheduleResponse,
    GoalTaskSchduleResponse,
    ConfirmAiPlanRequest
)

from app.workflows.redemption_workflow.schemas import RedeemRewardRequest,RedeemRewardResponse

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
    mediator: Mediator = Depends(get_create_task_with_schedule_mediator),
):
    schedule = None
    if payload.schedule is not None:
        schedule = CreateTaskScheduleDTO(**payload.schedule.model_dump())

    result = mediator.send(CreateTaskWithScheduleCommand(
        goal_id=goal_id,
        user_id=current_user.id,
        payload=CreateTaskWithScheduleDTO(
            task=CreateTaskDTO(**payload.task.model_dump()),
            schedule=schedule,
        ),
    ))
    return TaskWithScheduleResponse.model_validate(result, from_attributes=True)

@router.post(
        "/rewards/{reward_id}/redeem",
        response_model=RedeemRewardResponse,
        status_code=status.HTTP_200_OK)
def redemption_workflow(
    reward_id: int,
    current_user=Depends(get_current_user),
    mediator: Mediator = Depends(get_redeem_reward_mediator),
):
    result = mediator.send(RedeemRewardCommand(
        reward_id=reward_id,
        user_id=current_user.id,
    ))
    return RedeemRewardResponse.model_validate(result, from_attributes=True)


@router.post(
    "/ai/confirm",
    response_model=GoalTaskSchduleResponse,
    status_code=status.HTTP_201_CREATED,
)
def confirm_ai_plan(
    payload: ConfirmAiPlanRequest,
    current_user=Depends(get_current_user),
    task_workflow_service: TaskWorkflowServiceInterface = Depends(get_task_workflow_service),
                    )->GoalTaskSchduleResponse:
    return task_workflow_service.create_from_ai_plan(user_id=current_user.id, payload=payload)
