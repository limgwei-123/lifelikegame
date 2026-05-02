from app.tasks.repository import TaskRepository
from app.task_instances.repository import TaskInstanceRepository
from app.task_schedules.repository import TaskScheduleRepository
from app.task_instances.models import TaskInstance, TaskInstanceStatus
from datetime import date

from app.point_ledgers.interfaces import PointLedgerServiceInterface
from app.users.interfaces import UserServiceInterface

from app.task_schedules.models import ScheduleType

from app.shared.ownership import get_owned_task_or_raise, get_owned_task_schedule_or_raise, get_owned_task_instance_or_raise
from app.shared.enums import EntryType
from app.point_ledgers.schemas import CreatePointLedgerRequest
from app.task_instances.schemas import CompleteTaskInstanceResponse,TaskInstanceResponse

class TaskInstanceService:
  def __init__(self, task_instance_repo: TaskInstanceRepository, task_repo: TaskRepository,
               task_schedule_repo: TaskScheduleRepository, point_ledger_service: PointLedgerServiceInterface, user_service: UserServiceInterface):
    self.task_instance_repo = task_instance_repo
    self.task_repo = task_repo
    self.task_schedule_repo = task_schedule_repo
    self.point_ledger_service = point_ledger_service
    self.user_service = user_service

  def create_task_instance_for_date(self, task_id, task_schedule_id, user_id, date_instance):
    task = get_owned_task_or_raise(self.task_repo, task_id=task_id, user_id=user_id)
    task_schedule = get_owned_task_schedule_or_raise(self.task_schedule_repo, task_schedule_id=task_schedule_id, user_id=user_id)

    return self._create_task_instance(
      task=task,
      task_schedule=task_schedule,
      date_instance=date_instance,
    )


  #use for cron
  def generate_task_instances_for_date(self, target_date):
    task_schedules = self.task_schedule_repo.list_all()
    created_task_instance = []

    for task_schedule in task_schedules:
      if not self._should_generate_for_date(task_schedule, target_date):
        continue

      task = self.task_repo.get_by_id_and_user_id(task_id=task_schedule.task_id,user_id=task_schedule.user_id)
      if not task:
        continue

      task_instance = self._create_task_instance(
        task=task,
        task_schedule=task_schedule,
        date_instance=target_date
      )

      created_task_instance.append(task_instance)

    return created_task_instance


  def list_task_instances_by_date(self, user_id, date_instance: date):
    return self.task_instance_repo.list_by_user_id_and_date(user_id=user_id, date_instance = date_instance)

  def list_task_instances_by_month(self, user_id, year: int, month: int):

    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)


    return self.task_instance_repo.list_by_user_id_between_date(user_id=user_id, start_date=start_date, end_date=end_date)

  def complete_task_instance(
      self,
      task_instance_id:int,
      user_id,
      completion_level: str
  ):
    task_instance = get_owned_task_instance_or_raise(self.task_instance_repo, task_instance_id=task_instance_id, user_id=user_id)

    scoring_snapshot = task_instance.scoring_snapshot_json or {}
    if completion_level not in scoring_snapshot:
      raise ValueError("Invalid completion level")

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


    point_ledger_request = CreatePointLedgerRequest(
      delta=delta,
      entry_type=EntryType.EARN,
      source_type='task_instance',
      source_id= task_instance.id,
      description=f"Completed task instance #{task_instance.id}",
    )


    point_ledger = self.point_ledger_service.create_point_ledger(
      user_id=user_id,
      payload=point_ledger_request
    )

    user = self.user_service.update_user_point(user_id=user_id, delta=delta)

    return CompleteTaskInstanceResponse(
      task_instance=updated_instance,
      user=user,
      point_ledger=point_ledger
    )


  def _create_task_instance(self, task, task_schedule, date_instance):

    existing = self.task_instance_repo.get_by_task_id_and_date_instance(task_id=task.id, date_instance=date_instance)
    if existing:
      return existing

    task_instance = TaskInstance(
        user_id=task.user_id,
        task_schedule_id=task_schedule.id,
        task_id=task.id,
        date_instance=date_instance,
        status=TaskInstanceStatus.TODO.value,
        completion_level=None,
        score_awarded=0,
        scoring_snapshot_json=task.scoring_scheme_json,
        # generated_reason= "Everyday Auto"
    )

    return self.task_instance_repo.create(task_instance)

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

      return target_date.day == schedule_day

    return False