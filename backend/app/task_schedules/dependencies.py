from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.task_schedules.interfaces import TaskScheduleServiceInterface
from app.task_schedules.repository import TaskScheduleRepository
from app.tasks.repository import TaskRepository
from app.task_schedules.service import TaskScheduleService

def build_task_schedule_service(db: Session)->TaskScheduleServiceInterface:
  return TaskScheduleService(
    task_repo=TaskRepository(db),
    task_schedule_repo=TaskScheduleRepository(db)
  )

def get_task_schedule_service(
    db: Session = Depends(get_db)
)->TaskScheduleServiceInterface:
  return build_task_schedule_service(db)