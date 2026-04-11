from app.workflows.schemas import CreateTaskScheduleRequest, TaskScheduleResponse
from typing import Protocol

class WorkflowServiceInterface(Protocol):
  def create_task_with_schedule(
      self,
      goal_id: str,
      user_id: str,
      payload: CreateTaskScheduleRequest
  )->TaskScheduleResponse:
    ...