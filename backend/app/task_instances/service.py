from app.tasks.repository import TaskRepository
from app.task_instances.repository import TaskInstanceRepository
from app.task_schedules.repository import TaskScheduleRepository
from app.task_instances.models import TaskInstance, TaskInstanceStatus
from datetime import date

from app.shared.ownership import get_owned_task_or_raise, get_owned_task_schedule_or_raise, get_owned_task_instance_or_raise

class TaskInstanceService:
  def __init__(self, task_instance_repo: TaskInstanceRepository, task_repo: TaskRepository,
               task_schedule_repo: TaskScheduleRepository):
    self.task_instance_repo = task_instance_repo
    self.task_repo = task_repo
    self.task_schedule_repo = task_schedule_repo

  def create_task_instance(self, task_id, task_schedule_id, user_id):
    task = get_owned_task_or_raise(self.task_repo, task_id=task_id, user_id=user_id)
    task_schedule = get_owned_task_schedule_or_raise(self.task_schedule_repo, task_schedule_id=task_schedule_id, user_id=user_id)

    task_instance = TaskInstance(
      user_id = task.user_id,
      task_schedule_id = task_schedule.id,
      task_id = task.id,
      date_instance = date.today,
      status=TaskInstanceStatus.TODO.value,
      completion_level = None,
      score_awarded = 0,
      scoring_snapshot_json = task.scoring_scheme_json,
      generated_reason= "Everyday Auto"
    )

    return self.task_instance_repo.create(task_instance)

  def list_task_instances_by_date(self, user_id, date_instance: date):
    return self.task_instance_repo.list_by_user_id_and_date(user_id=user_id, date_instance = date_instance)

  def complete_task_instance(
      self,
      task_instance_id:int,
      user_id,
      completion_level: str
  ):
    task_instance = get_owned_task_instance_or_raise(self.task_instance_repo, task_instance_id=task_instance_id, user_id=user_id)

    snapshot = task_instance.scoring_snapshot_json or {}
    if completion_level not in snapshot:
      raise ValueError("Invalid completion level")

    old_score = task_instance.score_awarded
    new_score = int(snapshot[completion_level])
    delta = new_score - old_score

    task_instance.status = TaskInstanceStatus.DONE.value
    task_instance.completion_level =completion_level
    task_instance.score_awarded = new_score

    updated_instance = self.task_instance_repo.update(
      task_instance=task_instance
    )

    return {
      "task_instance": updated_instance,
      "delta": delta
    }