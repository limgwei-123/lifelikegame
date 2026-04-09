from typing import Protocol
from datetime import date

class TaskInstanceServiceInterface(Protocol):
  def create_task_instance_for_date(self, task_id, task_schedule_id, user_id,payload):
    ...

  def list_task_instances_by_date(self, user_id, date_instance: date):
    ...

  def complete_task_instance(
      self,
      task_instance_id:int,
      user_id,
      completion_level: str
  ):
    ...