from typing import Protocol
import uuid
from app.tasks.models import Task
from app.tasks.dtos import CreateTaskDTO, UpdateTaskDTO

class TaskServiceInterface(Protocol):
  def create_task(self, goal_id: int, user_id: uuid.UUID, payload: CreateTaskDTO) -> Task:
    ...

  def list_tasks_by_goal_id(self, goal_id: int, user_id: uuid.UUID) -> list[Task]:
    ...

  def list_tasks_by_user_id(self, user_id: uuid.UUID) -> list[Task]:
    ...

  def get_task_by_id(self, task_id: int, user_id: uuid.UUID) -> Task:
    ...

  def update_task(self, task_id: int, user_id: uuid.UUID, data: UpdateTaskDTO) -> Task:
    ...

  def delete_task(self, task_id: int, user_id: uuid.UUID) -> None:
    ...
