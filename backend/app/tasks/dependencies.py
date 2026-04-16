from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.tasks.interfaces import TaskServiceInterface
from app.tasks.repository import TaskRepository
from app.goals.repository import GoalRepository
from app.scoring_schemes.dependencies import build_scoring_scheme_service
from app.tasks.service import TaskService

def build_task_service(db:Session)->TaskServiceInterface:
  return TaskService(
    goal_repo=GoalRepository(db),
    task_repo=TaskRepository(db),
    scoring_scheme_service=build_scoring_scheme_service(db)
    )

def get_task_service(
    db: Session = Depends(get_db)
)->TaskServiceInterface:
  return build_task_service(db)