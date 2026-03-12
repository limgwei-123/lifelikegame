from fastapi import APIRouter, Depends, HTTPException, status
from app.goals.schemas import (
  CreateGoalRequest,
  GoalResponse
)
from sqlalchemy.orm import Session
from app.goals import service as goal_service
from app.auth.dependencies import get_current_user
from app.db import get_db

router = APIRouter(prefix="/goals", tags=["goals"])

@router.post('',response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(payload: CreateGoalRequest,
                current_user = Depends(get_current_user),
                db:Session = Depends(get_db),):
  try:
    goal = goal_service.create_goal(payload,
                                    user_id=current_user.id,
                                    db=db)
  except ValueError as e:
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail=str(e),
    )

  return goal
