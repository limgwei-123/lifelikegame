from app.workflows.task_workflow.schemas import CreateTaskScheduleRequest, TaskScheduleResponse,ConfirmAiPlanRequest, GoalTaskSchduleResponse
from typing import Protocol

class TaskWorkflowServiceInterface(Protocol):
  def create_task_with_schedule(
      self,
      goal_id: str,
      user_id: str,
      payload: CreateTaskScheduleRequest
  )->TaskScheduleResponse:
    ...

  def create_from_ai_plan(self, user_id, payload:ConfirmAiPlanRequest)->GoalTaskSchduleResponse:
    ...