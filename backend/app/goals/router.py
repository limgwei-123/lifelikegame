from fastapi import APIRouter, Depends, HTTPException, status
from app.auth.dependencies import get_current_user
from app.goals.schemas import (
  CreateGoalRequest,
  GoalResponse
)

from app.goals.interfaces import GoalServiceInterface
from app.goals.dependencies import get_goal_service


router = APIRouter(prefix="/goals", tags=["goals"])

@router.post('',response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(payload: CreateGoalRequest,
                current_user = Depends(get_current_user),
                goal_service: GoalServiceInterface = Depends(get_goal_service)):
  try:
    goal = goal_service.create_goal(payload,
                                    user_id=current_user.id)
  except ValueError as e:
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail=str(e),
    )

  return goal
