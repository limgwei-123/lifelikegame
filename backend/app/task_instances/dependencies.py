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


def build_task_instance_service(db: Session) -> TaskInstanceServiceInterface:
    return TaskInstanceService(
        task_repo=TaskRepository(db),
        task_schedule_repo=TaskScheduleRepository(db),
        task_instance_repo=TaskInstanceRepository(db),
    )


def get_task_instance_service(
    db: Session = Depends(get_db),
)->TaskInstanceServiceInterface:
  return build_task_instance_service(db)