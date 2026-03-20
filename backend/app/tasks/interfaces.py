from typing import Protocol
import uuid

class TaskServiceInterface(Protocol):
  def create_task(self, goal_id, user_id: uuid.UUID, payload):
    ...

  def list_tasks_by_goal_id(self, goal_id):
    ...

  def list_tasks_by_user_id(self, user_id):
    ...

  def get_task_by_id(self, task_id, user_id):
    ...

  def update_task(self, task_id, user_id, data):
    ...

  def delete_task(self, task_id, user_id):
    ...