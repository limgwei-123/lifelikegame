from app.task_instances.commands import CompleteTaskInstanceCommand
from app.task_instances.dtos import CompleteTaskInstanceResultDTO
from app.task_instances.interfaces import TaskInstanceServiceInterface


class CompleteTaskInstanceCommandHandler:
  def __init__(self, task_instance_service: TaskInstanceServiceInterface):
    self._task_instance_service = task_instance_service

  def handle(
      self,
      command: CompleteTaskInstanceCommand,
  ) -> CompleteTaskInstanceResultDTO:
    return self._task_instance_service.complete_task_instance(
      task_instance_id=command.task_instance_id,
      user_id=command.user_id,
      completion_level=command.completion_level,
    )
