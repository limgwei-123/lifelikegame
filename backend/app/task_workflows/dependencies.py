from app.tasks.dependencies import get_task_service
from app.task_schedules.dependencies import get_task_schedule_service
from app.task_workflows.interfaces import TaskWorkflowServiceInterface
from app.task_workflows.service import TaskWorkflowService
from fastapi import Depends

def get_task_workflow_service(
    task_service = Depends(get_task_service),
    task_schedule_service = Depends(get_task_schedule_service)
) -> TaskWorkflowServiceInterface:
  return TaskWorkflowService(
    task_service= task_service,
    task_schedule_service= task_schedule_service
  )