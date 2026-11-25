from app.task_instances.repository import TaskInstanceRepository
from app.task_instances.models import (
  ACTIVE_TASK_INSTANCE_UNIQUE_INDEX,
  TaskInstance,
  TaskInstanceStatus,
)
from datetime import date
from calendar import monthrange
from app.shared import dates
from sqlalchemy.exc import IntegrityError

from app.tasks.interfaces import TaskServiceInterface
from app.task_schedules.interfaces import TaskScheduleServiceInterface
from app.point_ledgers.interfaces import PointLedgerServiceInterface
from app.users.interfaces import UserServiceInterface

from app.task_schedules.models import ScheduleType

from app.errors.exception import ConflictError, NotFoundError, RequestValidationError
from app.shared.enums import EntryType
from app.point_ledgers.schemas import CreatePointLedgerRequest
from app.task_instances.dtos import CompleteTaskInstanceResultDTO, GenerateTaskInstancesResultDTO
from app.progress.service import ProgressService
from app.task_schedules.recurrence import MANAGED_RECURRENCE, next_on_or_after, tomorrow

class TaskInstanceService:
  def __init__(self, task_instance_repo: TaskInstanceRepository, task_service: TaskServiceInterface,
               task_schedule_service: TaskScheduleServiceInterface, point_ledger_service: PointLedgerServiceInterface,
               user_service: UserServiceInterface, progress_service: ProgressService):
    self.task_instance_repo = task_instance_repo
    self.task_service = task_service
    self.task_schedule_service = task_schedule_service
    self.point_ledger_service = point_ledger_service
    self.user_service = user_service
    self.progress_service = progress_service

  def create_task_instance_for_date(self, task_id, task_schedule_id, user_id, date_instance):
    task = self.task_service.get_task_by_id_for_update(task_id=task_id, user_id=user_id)
    task_schedule = self.task_schedule_service.get_task_schedule_by_id(task_schedule_id=task_schedule_id, user_id=user_id)
    if task_schedule.task_id != task.id:
      raise NotFoundError("Task Schedule not found")

    schedules = self._recurring_schedules(task)
    current = self._current_occurrence(task, schedules)
    if task_schedule.schedule_type == ScheduleType.ONCE and current is not None and current.generated_reason == MANAGED_RECURRENCE:
      if current.date_instance != date_instance or current.task_schedule_id != task_schedule.id:
        raise ConflictError('A current recurring occurrence already exists')
      return current

    if task_schedule.schedule_type != ScheduleType.ONCE:
      if not task.is_active:
        raise ConflictError('Inactive tasks cannot generate recurring occurrences')
      if current is not None and current.date_instance != date_instance:
        raise ConflictError('A current recurring occurrence already exists')
      if next_on_or_after(task_schedule, date_instance) != date_instance:
        raise RequestValidationError([{'field': 'date_instance', 'message': 'Date does not match the schedule', 'code': 'invalid_date'}])
      if current is not None:
        return current
      if self.task_instance_repo.has_managed_history(task.id):
        today = dates.player_today(task.user.timezone)
        current, _ = self._ensure_current(task, today)
        if current is None or current.date_instance != date_instance:
          raise ConflictError('Only the next scheduled occurrence can be created')
        return current
      existing = self.task_instance_repo.get_by_task_id_and_date_instance(task.id, date_instance)
      if existing is not None:
        return existing
      return self._create_task_instance_with_status(task, task_schedule, date_instance, recurring=True)[0]

    return self._create_task_instance(
      task=task,
      task_schedule=task_schedule,
      date_instance=date_instance,
    )


  #use for cron
  def generate_task_instances_for_date(self, target_date):
    return list(self.generate_task_instances_with_summary(target_date).task_instances)

  def generate_task_instances_with_summary(self, target_date: date | None) -> GenerateTaskInstancesResultDTO:
    task_schedules = self.task_schedule_service.list_task_schedules_for_generation()
    return self._generate_task_instances_from_schedules(target_date, task_schedules)

  def generate_task_instances_for_user(self, target_date: date, user_id) -> list[TaskInstance]:
    task_schedules = self.task_schedule_service.list_task_schedules_by_user_id(user_id)
    result = self._generate_task_instances_from_schedules(target_date, task_schedules)
    return list(result.task_instances)

  def _generate_task_instances_from_schedules(self, target_date, task_schedules):
    created_task_instance = []
    created_count = 0
    now = dates.utc_now() if target_date is None else None
    player_days = {}
    processed_tasks = set()

    for task_schedule in sorted(task_schedules, key=lambda schedule: (schedule.task_id, schedule.id)):
      if task_schedule.task_id in processed_tasks or task_schedule.schedule_type == ScheduleType.ONCE:
        continue
      processed_tasks.add(task_schedule.task_id)
      generation_date = target_date
      if generation_date is None:
        if task_schedule.user_id not in player_days:
          user = self.user_service.get_user_by_id(task_schedule.user_id)
          if user is None:
            continue
          player_days[task_schedule.user_id] = dates.player_today(user.timezone, now=now)
        generation_date = player_days[task_schedule.user_id]
      try:
        task = self.task_service.get_task_by_id_for_update(task_id=task_schedule.task_id, user_id=task_schedule.user_id)
      except NotFoundError:
        continue

      if not task.is_active:
        continue

      task_instance, was_created = self._ensure_current(task, generation_date)
      if task_instance is not None:
        created_task_instance.append(task_instance)
      created_count += int(was_created)

    return GenerateTaskInstancesResultDTO(
      target_date=target_date,
      task_instances=tuple(created_task_instance),
      processed_count=len(task_schedules),
      created_count=created_count,
    )


  def list_task_instances_by_date(self, user_id, date_instance: date):
    return self.task_instance_repo.list_by_user_id_and_date(user_id=user_id, date_instance = date_instance)

  def list_pending_task_instances(self, user_id, date_instance: date | None = None):
    user = self.user_service.get_user_by_id(user_id)
    if user is None:
      raise NotFoundError('User not found')
    cutoff = date_instance or dates.player_today(user.timezone)
    result, seen = [], set()
    for row in self.task_instance_repo.pending_for_user(user_id):
      try:
        task = self.task_service.get_task_by_id(row.task_id, user_id)
      except NotFoundError:
        continue
      if row.task_schedule.schedule_type == ScheduleType.ONCE and row.generated_reason != MANAGED_RECURRENCE:
        if row.date_instance <= cutoff:
          result.append(row)
      elif task.id not in seen:
        seen.add(task.id)
        current = self._current_occurrence(task, self._recurring_schedules(task))
        if current is not None and current.date_instance <= cutoff:
          result.append(current)
    return sorted(result, key=lambda row: (row.date_instance, row.id))

  def _recurring_schedules(self, task):
    return [schedule for schedule in self.task_schedule_service.list_task_schedules_by_task_id(task.id, task.user_id)
            if schedule.schedule_type != ScheduleType.ONCE and schedule.user_id == task.user_id]

  def _current_occurrence(self, task, schedules):
    schedule_ids = {schedule.id for schedule in schedules}
    owned = [row for row in self.task_instance_repo.pending_for_task(task.id)
             if row.user_id == task.user_id and row.task_schedule.task_id == task.id
             and row.task_schedule.user_id == task.user_id]
    managed = [row for row in owned if row.generated_reason == MANAGED_RECURRENCE]
    if managed:
      return managed[0]
    pending = [row for row in owned if row.task_schedule_id in schedule_ids]
    return pending[0] if pending and not self.task_instance_repo.has_managed_history(task.id) else None

  def _ensure_current(self, task, earliest):
    schedules = self._recurring_schedules(task)
    if not task.is_active:
      return None, False
    current = self._current_occurrence(task, schedules)
    if current is not None:
      if current.generated_reason != MANAGED_RECURRENCE:
        current.generated_reason = MANAGED_RECURRENCE
        self.task_instance_repo.update(current)
      return current, False
    if not schedules:
      return None, False
    last = self.task_instance_repo.latest_completed_date(task.id)
    if last is not None and last >= earliest:
      earliest = tomorrow(last)
    completed_at = self.task_instance_repo.latest_managed_completion_time(task.id)
    if completed_at is not None and earliest is not None:
      day_after_completion = tomorrow(dates.player_today(task.user.timezone, now=completed_at))
      if day_after_completion is None:
        return None, False
      earliest = max(earliest, day_after_completion)
    while earliest is not None:
      choices = [(day, schedule.id, schedule) for schedule in schedules
                 if (day := next_on_or_after(schedule, earliest)) is not None]
      if not choices:
        break
      day, _, schedule = min(choices)
      existing = self.task_instance_repo.get_by_task_id_and_date_instance(task.id, day)
      if existing is None:
        return self._create_task_instance_with_status(task, schedule, day, recurring=True)
      if existing.status == TaskInstanceStatus.TODO and existing.user_id == task.user_id and existing.task_schedule_id in {item.id for item in schedules}:
        existing.generated_reason = MANAGED_RECURRENCE
        return self.task_instance_repo.update(existing), False
      earliest = tomorrow(day)
    return None, False

  def list_task_instances_by_month(self, user_id, year: int, month: int):
    if not 1 <= year <= 9999 or not 1 <= month <= 12:
      raise RequestValidationError([{
        'field': 'year/month', 'message': 'Provide a valid calendar year and month', 'code': 'invalid_date',
      }])
    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])


    return self.task_instance_repo.list_by_user_id_between_date(user_id=user_id, start_date=start_date, end_date=end_date)

  def get_task_instance_by_id(self, task_instance_id, user_id):
    task_instance = self.task_instance_repo.get_by_id_and_user_id(task_instance_id, user_id)
    if not task_instance:
      raise NotFoundError("Task Instance not found")
    return task_instance

  def complete_task_instance(
      self,
      task_instance_id:int,
      user_id,
      completion_level: str | None = None
  ):
    original = self.get_task_instance_by_id(task_instance_id, user_id)
    task = self.task_service.get_task_by_id_for_update(original.task_id, user_id)
    task_instance = self.task_instance_repo.get_by_id_and_user_id_for_update(
      task_instance_id=task_instance_id,
      user_id=user_id,
    )
    if not task_instance:
      raise NotFoundError("Task Instance not found")

    completed_at = self.progress_service.current_time()

    was_done = task_instance.status == TaskInstanceStatus.DONE
    if not was_done and (task_instance.task_schedule.schedule_type != ScheduleType.ONCE
                         or task_instance.generated_reason == MANAGED_RECURRENCE):
      current = self._current_occurrence(task, self._recurring_schedules(task))
      # A deleted schedule may still have unfinished work, but never advances.
      if current is not None and current.id != task_instance.id:
        raise ConflictError('This occurrence is no longer the current recurring task')
      if current is None and self.task_instance_repo.has_managed_history(task.id) and task_instance.generated_reason != MANAGED_RECURRENCE:
        raise ConflictError('This historical occurrence is no longer current')
      today = dates.player_today(task.user.timezone, now=completed_at)
      if task_instance.generated_reason == MANAGED_RECURRENCE and task_instance.date_instance > today:
        raise RequestValidationError([{'field': 'date_instance', 'message': 'Future recurring tasks cannot be completed early', 'code': 'future_occurrence'}])
      task_instance.generated_reason = MANAGED_RECURRENCE

    if task.goal_id is None:
      if completion_level is not None:
        raise RequestValidationError([{
          "field": "completion_level", "message": "Standalone tasks do not accept a scoring level",
          "code": "unscored_task",
        }])
      task_instance.status = TaskInstanceStatus.DONE
      task_instance.completion_level = None
      task_instance.score_awarded = 0
      updated_instance = self.task_instance_repo.update(task_instance)
      return self._completion_result(updated_instance, user_id, was_done, False, None, completed_at)

    scoring_snapshot = task_instance.scoring_snapshot_json or {}
    if completion_level is None and len(scoring_snapshot) == 1:
      completion_level = next(iter(scoring_snapshot))
    if completion_level not in scoring_snapshot:
      raise RequestValidationError([{
        "field": "completion_level", "message": "Select a valid completion level", "code": "invalid_choice",
      }])

    score_awarded = scoring_snapshot[completion_level]



    old_score = task_instance.score_awarded
    new_score = int(scoring_snapshot[completion_level])
    delta = new_score - old_score

    task_instance.status = TaskInstanceStatus.DONE
    task_instance.completion_level =completion_level
    task_instance.score_awarded = score_awarded

    updated_instance = self.task_instance_repo.update(
      task_instance=task_instance
    )

    if delta == 0:
      return self._completion_result(updated_instance, user_id, was_done, True, None, completed_at)

    point_ledger_request = CreatePointLedgerRequest(
      delta=delta,
      entry_type=EntryType.EARN,
      source_type='task_instance',
      source_id= task_instance.id,
      description=f"Completed task instance #{task_instance.id}",
    )


    point_ledger = self.point_ledger_service.create_point_ledger(
      user_id=user_id,
      payload=point_ledger_request,
      occurred_at=completed_at,
    )

    return self._completion_result(updated_instance, user_id, was_done, True, point_ledger, completed_at)

  def _completion_result(self, task_instance, user_id, was_done, is_goal_task, point_ledger, completed_at):
    if not was_done:
      self.progress_service.record_completion(user_id, task_instance.id, is_goal_task, completed_at=completed_at)
    progress = self.progress_service.get_progress(user_id, as_of=completed_at)
    user = self.user_service.get_user_by_id(user_id=user_id)
    task = self.task_service.get_task_by_id(task_instance.task_id, user_id)
    next_instance = None
    if task_instance.task_schedule.schedule_type != ScheduleType.ONCE or task_instance.generated_reason == MANAGED_RECURRENCE:
      if not was_done:
        earliest = tomorrow(max(task_instance.date_instance, dates.player_today(user.timezone, now=completed_at)))
        if earliest is not None:
          next_instance = self._ensure_current(task, earliest)[0]
      else:
        next_instance = self._current_occurrence(task, self._recurring_schedules(task))
    return CompleteTaskInstanceResultDTO(
      task_instance=task_instance, user=user, point_ledger=point_ledger, progress=progress,
      next_task_instance=next_instance,
    )


  def _create_task_instance(self, task, task_schedule, date_instance):
    task_instance, _ = self._create_task_instance_with_status(
      task, task_schedule, date_instance,
    )
    return task_instance

  def _create_task_instance_with_status(self, task, task_schedule, date_instance, recurring=False):

    existing = self.task_instance_repo.get_by_task_id_and_date_instance(task_id=task.id, date_instance=date_instance)
    if existing:
      return existing, False

    task_instance = TaskInstance(
        user_id=task.user_id,
        task_schedule_id=task_schedule.id,
        task_id=task.id,
        date_instance=date_instance,
        status=TaskInstanceStatus.TODO.value,
        completion_level=None,
        score_awarded=0,
        scoring_snapshot_json=task.scoring_scheme_json,
        generated_reason=MANAGED_RECURRENCE if recurring else None,
        # generated_reason= "Everyday Auto"
    )

    try:
      return self.task_instance_repo.create(task_instance), True
    except IntegrityError as error:
      constraint_name = getattr(
        getattr(error.orig, "diag", None),
        "constraint_name",
        None,
      )
      if constraint_name == ACTIVE_TASK_INSTANCE_UNIQUE_INDEX:
        raise ConflictError(
          "Task instance already exists for this task and date"
        ) from error
      raise

  def _should_generate_for_date(self, task_schedule, target_date):

  # start_date 检查
    if task_schedule.start_date and target_date < task_schedule.start_date:
        return False
    # end_date 检查
    if task_schedule.end_date and target_date > task_schedule.end_date:
        return False


    if task_schedule.schedule_type == ScheduleType.DAILY:
        return True

    elif task_schedule.schedule_type == ScheduleType.WEEKLY:
      schedule_days = task_schedule.schedule_value_json.get("days", [])

      if not schedule_days:
        return False

      weekday = target_date.weekday()
      return weekday in schedule_days

    elif task_schedule.schedule_type == ScheduleType.MONTHLY:
      schedule_day = task_schedule.schedule_value_json.get("day")

      if schedule_day is None:
        return False

      # Missing monthly dates are skipped, never clamped or carried forward.
      return target_date.day == schedule_day

    return False
