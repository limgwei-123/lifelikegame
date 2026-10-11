import uuid
from typing import Protocol
from app.workflows.task_workflow.dtos import (
    CreateTaskWithScheduleDTO,
    TaskWithScheduleResultDTO,
)
from app.workflows.task_workflow.schemas import (
    GoalTaskSchduleResponse,
)
from app.ai_planner.draft_schemas import DraftPlan

class TaskWorkflowServiceInterface(Protocol):
  def create_task_with_schedule(
      self,
      goal_id: int,
      user_id: uuid.UUID,
      payload: CreateTaskWithScheduleDTO
  ) -> TaskWithScheduleResultDTO:
    ...

  def create_from_ai_plan(self, user_id: uuid.UUID, plan: DraftPlan) -> GoalTaskSchduleResponse:
    ...
