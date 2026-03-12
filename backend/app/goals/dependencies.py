from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.goals.interfaces import GoalServiceInterface
from app.goals.repository import GoalRepository
from app.goals.service import GoalService

def get_goal_repository(
    db: Session = Depends(get_db)
)-> GoalRepository:
  return GoalRepository(db)

def get_goal_service(
    goal_repo: GoalRepository = Depends(get_goal_repository)
)->GoalServiceInterface:
  return GoalService(goal_repo)