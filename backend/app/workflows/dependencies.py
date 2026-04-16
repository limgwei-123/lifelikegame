from app.tasks.dependencies import build_task_service
from app.task_schedules.dependencies import build_task_schedule_service
from app.goals.dependencies import build_goal_service
from app.task_instances.dependencies import build_task_instance_service
from app.scoring_schemes.dependencies import build_scoring_scheme_service
from app.workflows.interfaces import WorkflowServiceInterface
from app.workflows.service import WorkflowService
from fastapi import Depends
from sqlalchemy.orm import Session
from app.db import get_db

def build_workflow_service(db: Session)-> WorkflowServiceInterface:
  return WorkflowService(
    task_service= build_task_service(db),
    task_schedule_service= build_task_schedule_service(db),
    goal_service = build_goal_service(db),
    task_instance_service = build_task_instance_service(db),
    scoring_scheme_service=build_scoring_scheme_service(db)
  )

def get_workflow_service(
    db: Session = Depends(get_db),
) -> WorkflowServiceInterface:
    return build_workflow_service(db)