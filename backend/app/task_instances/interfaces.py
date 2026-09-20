from typing import Protocol
from datetime import date
import uuid
from app.task_instances.models import TaskInstance
from app.task_instances.schemas import CompleteTaskInstanceResponse

class TaskInstanceServiceInterface(Protocol):
  def get_task_instance_by_id(self, task_instance_id: int, user_id: uuid.UUID) -> TaskInstance:
    ...

  def create_task_instance_for_date(
      self,
      task_id: int,
      task_schedule_id: int,
      user_id: uuid.UUID,
      date_instance: date
  ) -> TaskInstance:
    ...

  def generate_task_instances_for_date(self, target_date: date) -> list[TaskInstance]:
    ...

  def list_task_instances_by_date(self, user_id: uuid.UUID, date_instance: date) -> list[TaskInstance]:
    ...

  def complete_task_instance(
      self,
      task_instance_id: int,
      user_id: uuid.UUID,
      completion_level: str
  ) -> CompleteTaskInstanceResponse:
    ...

  def list_task_instances_by_month(self, user_id: uuid.UUID, year: int, month: int) -> list[TaskInstance]:
    ...
