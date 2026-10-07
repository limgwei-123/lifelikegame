from app.task_instances.commands import (
  CompleteTaskInstanceCommand,
  GenerateDailyTaskInstancesCommand,
)
from app.task_instances.dtos import (
  CompleteTaskInstanceResultDTO,
  GenerateTaskInstancesResultDTO,
)
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


class GenerateDailyTaskInstancesCommandHandler:
  def __init__(self, task_instance_service: TaskInstanceServiceInterface):
    self._task_instance_service = task_instance_service

  def handle(
      self,
      command: GenerateDailyTaskInstancesCommand,
  ) -> GenerateTaskInstancesResultDTO:
    task_instances = self._task_instance_service.generate_task_instances_for_date(
      target_date=command.target_date,
    )
    return GenerateTaskInstancesResultDTO(
      target_date=command.target_date,
      task_instances=tuple(task_instances),
    )
