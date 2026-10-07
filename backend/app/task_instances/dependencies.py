from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.behaviors import LoggingBehavior, TransactionBehavior, ValidationBehavior, ValidatorRegistry
from app.core.mediator import HandlerRegistry, Mediator
from app.core.unit_of_work import build_unit_of_work
from app.db import get_db, get_session
from app.task_instances.commands import CompleteTaskInstanceCommand
from app.task_instances.handlers import CompleteTaskInstanceCommandHandler
from app.task_instances.interfaces import TaskInstanceServiceInterface
from app.task_instances.repository import TaskInstanceRepository
from app.tasks.dependencies import build_task_service
from app.task_schedules.dependencies import build_task_schedule_service

from app.task_instances.service import TaskInstanceService

from app.point_ledgers.dependencies import build_point_ledger_service
from app.users.dependencies import build_user_service
from app.task_instances.validators import CompleteTaskInstanceCommandValidator


def build_task_instance_service(db: Session) -> TaskInstanceServiceInterface:

    return TaskInstanceService(
        task_service=build_task_service(db),
        task_schedule_service=build_task_schedule_service(db),
        task_instance_repo=TaskInstanceRepository(db),
        point_ledger_service=build_point_ledger_service(db),
        user_service=build_user_service(db)
    )


def get_task_instance_service(
    db: Session = Depends(get_db),
)->TaskInstanceServiceInterface:
  return build_task_instance_service(db)


def build_complete_task_instance_mediator(db: Session) -> Mediator:
  handler_registry = HandlerRegistry()
  handler_registry.register(
    CompleteTaskInstanceCommand,
    CompleteTaskInstanceCommandHandler(build_task_instance_service(db)),
  )

  validator_registry = ValidatorRegistry()
  validator_registry.register(
    CompleteTaskInstanceCommand,
    CompleteTaskInstanceCommandValidator(),
  )

  return Mediator(
    handler_registry,
    behaviors=[
      LoggingBehavior(),
      ValidationBehavior(validator_registry),
      TransactionBehavior(build_unit_of_work(db)),
    ],
  )


def get_complete_task_instance_mediator(
    db: Session = Depends(get_session),
) -> Mediator:
  return build_complete_task_instance_mediator(db)
