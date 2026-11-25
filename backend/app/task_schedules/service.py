from app.tasks.interfaces import TaskServiceInterface
from app.task_schedules.dtos import CreateTaskScheduleDTO
from app.task_schedules.repository import TaskScheduleRepository
from app.task_schedules.schemas import UpdateTaskScheduleRequest
from app.task_schedules.schemas import WeeklyValue, MonthlyValue
from app.task_schedules.models import ScheduleType
from pydantic import ValidationError

from app.errors.exception import NotFoundError, RequestValidationError
from app.task_schedules.models import TaskSchedule
from app.shared.dates import player_today
class TaskScheduleService:
  def __init__(self, task_schedule_repo: TaskScheduleRepository, task_service: TaskServiceInterface):
    self.task_schedule_repo = task_schedule_repo
    self.task_service = task_service


  def create_task_schedule(self, task_id, user_id, payload: CreateTaskScheduleDTO):
    task = self.task_service.get_task_by_id(task_id=task_id, user_id=user_id)

    start_date = payload.start_date if payload.start_date is not None else player_today(task.user.timezone)
    self._validate_date_range(start_date, payload.end_date)

    self._validate_schedule_value(
    schedule_type=payload.schedule_type,
    schedule_value_json=payload.schedule_value_json,
    )

    task_schedule = TaskSchedule(
      user_id = user_id,
      task_id = task.id,
      schedule_type= payload.schedule_type,
      schedule_value_json= payload.schedule_value_json,
      start_date=start_date,
      end_date= payload.end_date
    )

    return self.task_schedule_repo.create(task_schedule)

  def list_all_task_schedules(self):
    return self.task_schedule_repo.list_all()

  def list_task_schedules_for_generation(self):
    return self.task_schedule_repo.list_for_generation()

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
    update_task_schedule = data.model_dump(exclude_unset=True)

    self._validate_date_range(
      update_task_schedule.get("start_date", task_schedule.start_date),
      update_task_schedule.get("end_date", task_schedule.end_date),
    )

    self._validate_schedule_value(
    schedule_type=data.schedule_type,
    schedule_value_json=data.schedule_value_json,
    )

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
      try:
        WeeklyValue(**schedule_value_json)
      except ValidationError as error:
        raise RequestValidationError([{
          "field": "schedule_value_json.days",
          "message": "Weekly days must be a non-empty list of integers between 0 and 6",
          "code": "weekly_days",
        }]) from error

    elif schedule_type == ScheduleType.MONTHLY:
      try:
        MonthlyValue(**schedule_value_json)
      except ValidationError as error:
        raise RequestValidationError([{
          "field": "schedule_value_json.day",
          "message": "Monthly day must be an integer between 1 and 31",
          "code": "monthly_day",
        }]) from error

  def _validate_date_range(self, start_date, end_date):
    if start_date is not None and end_date is not None and end_date < start_date:
      raise RequestValidationError([{
        "field": "schedule.end_date",
        "message": "End date must not be before start date",
        "code": "date_range",
      }])
