from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.goals.interfaces import GoalServiceInterface
from app.goals.repository import GoalRepository
from app.goals.service import GoalService
from app.users.dependencies import build_user_service


def build_goal_service(db:Session)->GoalServiceInterface:
  return GoalService(
    goal_repo=GoalRepository(db), user_service=build_user_service(db)
  )

def get_goal_service(
    db:Session = Depends(get_db, scope="function")
)->GoalServiceInterface:
  return build_goal_service(db)
