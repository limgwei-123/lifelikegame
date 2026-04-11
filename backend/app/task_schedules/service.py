from app.tasks.repository import TaskRepository
from app.task_schedules.repository import TaskScheduleRepository
from app.task_schedules.schemas import CreateTaskScheduleRequest, UpdateTaskScheduleRequest
from app.task_schedules.schemas import WeeklyValue, MonthlyValue
from app.task_schedules.models import ScheduleType

from app.shared.ownership import get_owned_task_or_raise, get_owned_task_schedule_or_raise

class TaskScheduleService:
  def __init__(self, task_schedule_repo: TaskScheduleRepository, task_repo: TaskRepository):
    self.task_schedule_repo = task_schedule_repo
    self.task_repo = task_repo


  def create_task_schedule(self, task_id, user_id, payload: CreateTaskScheduleRequest):
    task = get_owned_task_or_raise(self.task_repo, task_id, user_id)
    data = payload.model_dump()
    data['user_id'] = task.user_id
    data['task_id'] = task.id

    self._validate_schedule_value(
    schedule_type=payload.schedule_type,
    schedule_value_json=payload.schedule_value_json,
    )

    return self.task_schedule_repo.create(data)

  def list_all_task_schedules(self):
    return self.task_schedule_repo.list_all()

  def list_task_schedules_by_task_id(self, task_id, user_id):
    task = get_owned_task_or_raise(self.task_repo,task_id = task_id, user_id = user_id)
    return self.task_schedule_repo.list_by_task_id(task.id)

  def list_task_schedules_by_user_id(self, user_id):
    return self.task_schedule_repo.list_by_user_id(user_id)

  def get_task_schedule_by_id(self, task_schedule_id, user_id):
    get_owned_task_schedule_or_raise(self.task_schedule_repo,task_schedule_id, user_id)
    return self.task_schedule_repo.get_by_id(task_schedule_id)

  def update_task_schedule(self, task_schedule_id, user_id, data: UpdateTaskScheduleRequest):
    task_schedule = get_owned_task_schedule_or_raise(self.task_schedule_repo,task_schedule_id, user_id)

    self._validate_schedule_value(
    schedule_type=data.schedule_type,
    schedule_value_json=data.schedule_value_json,
    )


    return self.task_schedule_repo.update(
      task_schedule,
      data.model_dump(exclude_unset=True)
    )

  def delete_task_schedule(self, task_schedule_id, user_id):
    task_schedule = get_owned_task_schedule_or_raise(self.task_schedule_repo,task_schedule_id, user_id)

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