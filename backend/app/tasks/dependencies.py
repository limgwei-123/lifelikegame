from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.tasks.interfaces import TaskServiceInterface
from app.tasks.repository import TaskRepository
from app.goals.repository import GoalRepository
from app.tasks.service import TaskService

def get_task_repository(
    db: Session = Depends(get_db)
)->TaskRepository:
  return TaskRepository(db)

def get_goal_repository(
    db: Session = Depends(get_db)
)-> GoalRepository:
  return GoalRepository(db)

def get_task_service(
    task_repo: TaskRepository = Depends (get_task_repository),
    goal_repo: GoalRepository = Depends (get_goal_repository)
)->TaskServiceInterface:
  return TaskService(goal_repo=goal_repo, task_repo=task_repo)