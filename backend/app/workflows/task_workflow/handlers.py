from app.workflows.task_workflow.commands import CreateTaskWithScheduleCommand
from app.workflows.task_workflow.dtos import TaskWithScheduleResultDTO
from app.workflows.task_workflow.interfaces import TaskWorkflowServiceInterface


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
