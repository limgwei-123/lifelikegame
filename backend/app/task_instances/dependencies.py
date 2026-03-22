from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.task_instances.interfaces import TaskInstanceServiceInterface
from app.task_instances.repository import TaskInstanceRepository
from app.tasks.repository import TaskRepository
from app.task_schedules.repository import TaskScheduleRepository
from app.task_instances.service import TaskInstanceService

def get_task_instance_repository(
    db: Session = Depends(get_db)
)->TaskInstanceRepository:
  return TaskInstanceRepository(db)

def get_task_repository(
    db:Session = Depends(get_db)
)->TaskRepository:
  return TaskRepository(db)

def get_task_schedule_repository(
    db:Session = Depends(get_db)
)->TaskScheduleRepository:
  return TaskScheduleRepository(db)

def get_task_instance_service(
    task_repo: TaskRepository = Depends(get_task_repository),
    task_schedule_repo: TaskScheduleRepository = Depends(get_task_schedule_repository),
    task_instance_repo: TaskInstanceRepository = Depends(get_task_instance_repository)
)->TaskInstanceServiceInterface:
  return TaskInstanceService(
    task_repo=task_repo,
    task_instance_repo=task_instance_repo,
    task_schedule_repo = task_schedule_repo)