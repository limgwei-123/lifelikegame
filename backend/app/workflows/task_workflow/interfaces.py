from app.workflows.task_workflow.schemas import CreateTaskScheduleRequest, TaskScheduleResponse
from typing import Protocol

class TaskWorkflowServiceInterface(Protocol):
  def create_task_with_schedule(
      self,
      goal_id: str,
      user_id: str,
      payload: CreateTaskScheduleRequest
  )->TaskScheduleResponse:
    ...
