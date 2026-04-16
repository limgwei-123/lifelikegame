from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.task_instances.interfaces import TaskInstanceServiceInterface
from app.task_instances.repository import TaskInstanceRepository
from app.tasks.repository import TaskRepository
from app.task_schedules.repository import TaskScheduleRepository

from app.task_instances.service import TaskInstanceService

from app.point_ledgers.dependencies import build_point_ledger_service
from app.users.dependencies import build_user_service


def build_task_instance_service(db: Session) -> TaskInstanceServiceInterface:

    return TaskInstanceService(
        task_repo=TaskRepository(db),
        task_schedule_repo=TaskScheduleRepository(db),
        task_instance_repo=TaskInstanceRepository(db),
        point_ledger_service=build_point_ledger_service(db),
        user_service=build_user_service(db)
    )


def get_task_instance_service(
    db: Session = Depends(get_db),
)->TaskInstanceServiceInterface:
  return build_task_instance_service(db)