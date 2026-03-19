from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.task_schedules.interfaces import TaskScheduleServiceInterface
from app.task_schedules.repository import TaskScheduleRepository
from app.tasks.repository import TaskRepository
from app.task_schedules.service import TaskScheduleService

def get_task_schedule_repository(
    db: Session = Depends(get_db)
)->TaskScheduleRepository:
  return TaskScheduleRepository(db)

def get_task_repository(
    db: Session = Depends(get_db)
)-> TaskRepository:
  return TaskRepository(db)

def get_task_schedule_service(
    task_schedule_repo: TaskScheduleRepository = Depends (get_task_schedule_repository),
    task_repo: TaskRepository = Depends (get_task_repository)
)->TaskScheduleServiceInterface:
  return TaskScheduleService(task_schedule_repo=task_schedule_repo, task_repo=task_repo)