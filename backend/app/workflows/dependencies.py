from app.tasks.dependencies import get_task_service
from app.task_schedules.dependencies import get_task_schedule_service
from app.goals.dependencies import get_goal_service
from app.task_instances.dependencies import get_task_instance_service
from app.workflows.interfaces import WorkflowServiceInterface
from app.workflows.service import WorkflowService
from fastapi import Depends

def get_workflow_service(
    task_service = Depends(get_task_service),
    task_schedule_service = Depends(get_task_schedule_service),
    goal_service = Depends(get_goal_service),
    task_instance_service = Depends(get_task_instance_service)
) -> WorkflowServiceInterface:
  return WorkflowService(
    task_service= task_service,
    task_schedule_service= task_schedule_service,
    goal_service = goal_service,
    task_instance_service = task_instance_service,
  )