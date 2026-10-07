from dataclasses import dataclass

from app.task_instances.models import TaskInstance
from app.task_schedules.dtos import CreateTaskScheduleDTO
from app.task_schedules.models import TaskSchedule
from app.tasks.dtos import CreateTaskDTO
from app.tasks.models import Task


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateTaskWithScheduleDTO:
  task: CreateTaskDTO
  schedule: CreateTaskScheduleDTO | None = None


@dataclass(frozen=True, slots=True)
class TaskWithScheduleResultDTO:
  task: Task
  schedule: TaskSchedule | None
  task_instance: TaskInstance | None
