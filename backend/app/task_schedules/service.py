from app.tasks.interfaces import TaskServiceInterface
from app.task_schedules.repository import TaskScheduleRepository
from app.task_schedules.schemas import CreateTaskScheduleRequest, UpdateTaskScheduleRequest
from app.task_schedules.schemas import WeeklyValue, MonthlyValue
from app.task_schedules.models import ScheduleType

from app.errors.exception import NotFoundError
from app.task_schedules.models import TaskSchedule
class TaskScheduleService:
  def __init__(self, task_schedule_repo: TaskScheduleRepository, task_service: TaskServiceInterface):
    self.task_schedule_repo = task_schedule_repo
    self.task_service = task_service


  def create_task_schedule(self, task_id, user_id, payload: CreateTaskScheduleRequest):
    task = self.task_service.get_task_by_id(task_id=task_id, user_id=user_id)

    self._validate_schedule_value(
    schedule_type=payload.schedule_type,
    schedule_value_json=payload.schedule_value_json,
    )

    task_schedule = TaskSchedule(
      user_id = user_id,
      task_id = task.id,
      schedule_type= payload.schedule_type,
      schedule_value_json= payload.schedule_value_json,
      start_date= payload.start_date,
      end_date= payload.end_date
    )

    return self.task_schedule_repo.create(task_schedule)

  def list_all_task_schedules(self):
    return self.task_schedule_repo.list_all()

  def list_task_schedules_by_task_id(self, task_id, user_id):
    task = self.task_service.get_task_by_id(task_id=task_id, user_id=user_id)
    return self.task_schedule_repo.list_by_task_id(task.id)

  def list_task_schedules_by_user_id(self, user_id):
    return self.task_schedule_repo.list_by_user_id(user_id)

  def get_task_schedule_by_id(self, task_schedule_id, user_id):
    task_schedule = self.task_schedule_repo.get_by_id_and_user_id(task_schedule_id, user_id)
    if not task_schedule:
      raise NotFoundError("Task Schedule not found")
    return task_schedule

  def update_task_schedule(self, task_schedule_id, user_id, data: UpdateTaskScheduleRequest):
    task_schedule = self.get_task_schedule_by_id(task_schedule_id=task_schedule_id, user_id=user_id)

    self._validate_schedule_value(
    schedule_type=data.schedule_type,
    schedule_value_json=data.schedule_value_json,
    )

    update_task_schedule = data.model_dump(exclude_unset=True)

    for field, value in update_task_schedule.items():
        setattr(task_schedule, field, value)

    return self.task_schedule_repo.update(
      task_schedule
    )

  def delete_task_schedule(self, task_schedule_id, user_id):
    task_schedule = self.get_task_schedule_by_id(task_schedule_id=task_schedule_id, user_id=user_id)

    self.task_schedule_repo.delete(task_schedule)

  def _validate_schedule_value(self, schedule_type, schedule_value_json):
    if schedule_type == ScheduleType.WEEKLY:
      validated = WeeklyValue(**schedule_value_json)
      days = validated.days

      if len(days) == 0:
        raise ValueError("days cannot be empty")

      for day in days:
        if day < 0 or day > 6:
          raise ValueError("each day must be between 0 and 6")

    elif schedule_type == ScheduleType.MONTHLY:
      validated = MonthlyValue(**schedule_value_json)
      day = validated.day

      if day < 1 or day > 31:
          raise ValueError("day must be between 1 and 31")
