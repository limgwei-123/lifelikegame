from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_user
from app.goals.schemas import (
  CreateGoalRequest,
  UpdateGoalRequest,
  GoalResponse
)

from app.goals.interfaces import GoalServiceInterface
from app.goals.dependencies import get_goal_service


router = APIRouter(prefix="/goals", tags=["goals"])

@router.post('',response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(payload: CreateGoalRequest,
                current_user = Depends(get_current_user),
                goal_service: GoalServiceInterface = Depends(get_goal_service),
                ):
    return goal_service.create_goal(
                                    user_id=current_user.id, payload = payload)

@router.get("", response_model= list[GoalResponse] , status_code= status.HTTP_200_OK)
def list_goals(current_user = Depends(get_current_user),
               goal_service: GoalServiceInterface = Depends(get_goal_service)):
    return goal_service.list_goals(current_user.id)

@router.get('/{goal_id}', response_model= GoalResponse, status_code= status.HTTP_200_OK)
def get_goal_by_id(goal_id,
                   current_user = Depends(get_current_user),
                   goal_service: GoalServiceInterface = Depends(get_goal_service)):
    return goal_service.get_goal_by_id(goal_id, current_user.id)

@router.post("/{goal_id}", response_model= GoalResponse)
def update_goal(goal_id,
                paylod:UpdateGoalRequest,
                current_user = Depends(get_current_user),
                goal_service: GoalServiceInterface = Depends(get_goal_service)):
    return goal_service.update_goal(
        goal_id = goal_id,
        user_id = current_user.id,
        data = paylod
    )

@router.post("/{goal_id}/delete", status_code=204)
def delete_goal(
    goal_id,
    current_user = Depends(get_current_user),
    goal_service: GoalServiceInterface = Depends(get_goal_service)
):
    goal_service.delete_goal(goal_id, current_user.id)



