from app.ai_planner.dependencies import build_ai_draft_service
from app.tasks.dependencies import build_task_service
from app.task_schedules.dependencies import build_task_schedule_service
from app.goals.dependencies import build_goal_service
from app.task_instances.dependencies import build_task_instance_service
from app.scoring_schemes.dependencies import build_scoring_scheme_service

from app.core.behaviors import LoggingBehavior, TransactionBehavior, ValidationBehavior, ValidatorRegistry
from app.core.mediator import HandlerRegistry, Mediator
from app.core.unit_of_work import build_unit_of_work
from app.workflows.task_workflow.commands import ConfirmAiPlanCommand, CreateTaskWithScheduleCommand
from app.workflows.task_workflow.handlers import ConfirmAiPlanCommandHandler, CreateTaskWithScheduleCommandHandler
from app.workflows.task_workflow.interfaces import TaskWorkflowServiceInterface
from app.workflows.task_workflow.service import TaskWorkflowService
from app.workflows.task_workflow.validators import ConfirmAiPlanCommandValidator, CreateTaskWithScheduleCommandValidator
from fastapi import Depends
from sqlalchemy.orm import Session
from app.db import get_db, get_session

def build_task_workflow_service(db: Session)-> TaskWorkflowServiceInterface:
  return TaskWorkflowService(
    task_service= build_task_service(db),
    task_schedule_service= build_task_schedule_service(db),
    goal_service = build_goal_service(db),
    task_instance_service = build_task_instance_service(db),
    scoring_scheme_service=build_scoring_scheme_service(db),
  )

def get_task_workflow_service(
    db: Session = Depends(get_db, scope="function"),
) -> TaskWorkflowServiceInterface:
    return build_task_workflow_service(db)


def build_create_task_with_schedule_mediator(db: Session) -> Mediator:
  handler_registry = HandlerRegistry()
  handler_registry.register(
    CreateTaskWithScheduleCommand,
    CreateTaskWithScheduleCommandHandler(build_task_workflow_service(db)),
  )

  validator_registry = ValidatorRegistry()
  validator_registry.register(
    CreateTaskWithScheduleCommand,
    CreateTaskWithScheduleCommandValidator(),
  )

  return Mediator(
    handler_registry,
    behaviors=[
      LoggingBehavior(),
      ValidationBehavior(validator_registry),
      TransactionBehavior(build_unit_of_work(db)),
    ],
  )


def get_create_task_with_schedule_mediator(
    db: Session = Depends(get_session),
) -> Mediator:
  return build_create_task_with_schedule_mediator(db)


def build_confirm_ai_plan_mediator(db: Session) -> Mediator:
  handler_registry = HandlerRegistry()
  handler_registry.register(
    ConfirmAiPlanCommand,
    ConfirmAiPlanCommandHandler(build_ai_draft_service(db), build_task_workflow_service(db)),
  )

  validator_registry = ValidatorRegistry()
  validator_registry.register(ConfirmAiPlanCommand, ConfirmAiPlanCommandValidator())

  return Mediator(
    handler_registry,
    behaviors=[
      LoggingBehavior(),
      ValidationBehavior(validator_registry),
      TransactionBehavior(build_unit_of_work(db)),
    ],
  )


def get_confirm_ai_plan_mediator(db: Session = Depends(get_session)) -> Mediator:
  return build_confirm_ai_plan_mediator(db)
