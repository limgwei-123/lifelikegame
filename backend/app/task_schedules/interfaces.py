from typing import Protocol
import uuid

class TaskScheduleServiceInterface(Protocol):
  def create_task_schedule(self, task_id, user_id: uuid.UUID, payload):
    ...

  def list_task_schedules_by_task_id(self, task_id):
    ...

  def list_task_schedules_by_user_id(self, user_id):
    ...

  def get_task_schedule_by_id(self, task_schedule_id, user_id):
    ...

  def update_task_schedule(self, task_schedule_id, user_id, data):
    ...

  def delete_task_schedule(self, task_schedule_id, user_id):
    ...