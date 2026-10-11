from app.ai_planner.draft_service import AIPlanDraftService
from app.workflows.task_workflow.commands import ConfirmAiPlanCommand, CreateTaskWithScheduleCommand
from app.workflows.task_workflow.dtos import TaskWithScheduleResultDTO
from app.workflows.task_workflow.interfaces import TaskWorkflowServiceInterface
from app.workflows.task_workflow.schemas import GoalTaskSchduleResponse


class CreateTaskWithScheduleCommandHandler:
  def __init__(self, task_workflow_service: TaskWorkflowServiceInterface):
    self._task_workflow_service = task_workflow_service

  def handle(
      self,
      command: CreateTaskWithScheduleCommand,
  ) -> TaskWithScheduleResultDTO:
    return self._task_workflow_service.create_task_with_schedule(
      goal_id=command.goal_id,
      user_id=command.user_id,
      payload=command.payload,
    )


class ConfirmAiPlanCommandHandler:
  def __init__(
      self,
      draft_service: AIPlanDraftService,
      task_workflow_service: TaskWorkflowServiceInterface,
  ):
    self._draft_service = draft_service
    self._task_workflow_service = task_workflow_service

  def handle(self, command: ConfirmAiPlanCommand) -> GoalTaskSchduleResponse:
    return self._draft_service.confirm(
      user_id=command.user_id,
      draft_id=command.draft_id,
      task_workflow_service=self._task_workflow_service,
    )
