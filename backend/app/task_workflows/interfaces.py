from app.tasks.schemas import CreateTaskRequest
from typing import Protocol

class TaskWorkflowServiceInterface(Protocol):
  def create_task_with_schedule(
      self,
      goal_id: str,
      user_id: str,
      payload: CreateTaskRequest
  ):
    ...