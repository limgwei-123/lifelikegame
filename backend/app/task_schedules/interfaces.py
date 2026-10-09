from typing import Protocol
import uuid
from app.task_schedules.dtos import CreateTaskScheduleDTO
from app.task_schedules.models import TaskSchedule
from app.task_schedules.schemas import UpdateTaskScheduleRequest

class TaskScheduleServiceInterface(Protocol):
  def create_task_schedule(self, task_id: int, user_id: uuid.UUID, payload: CreateTaskScheduleDTO) -> TaskSchedule:
    ...

  def list_all_task_schedules(self) -> list[TaskSchedule]:
    ...

  def list_task_schedules_for_generation(self) -> list[TaskSchedule]:
    ...

  def list_task_schedules_by_task_id(self, task_id: int, user_id: uuid.UUID) -> list[TaskSchedule]:
    ...

  def list_task_schedules_by_user_id(self, user_id: uuid.UUID) -> list[TaskSchedule]:
    ...

  def get_task_schedule_by_id(self, task_schedule_id: int, user_id: uuid.UUID) -> TaskSchedule:
    ...

  def update_task_schedule(self, task_schedule_id: int, user_id: uuid.UUID, data: UpdateTaskScheduleRequest) -> TaskSchedule:
    ...

  def delete_task_schedule(self, task_schedule_id: int, user_id: uuid.UUID) -> None:
    ...
