from app.tasks.repository import TaskRepository
from app.task_instances.repository import TaskInstanceRepository
from app.task_schedules.repository import TaskScheduleRepository
from app.task_instances.schemas import CompleteTaskInstanceRequest
from app.task_instances.models import TaskInstance, TaskInstanceStatus
from datetime import date

from app.errors.exception import NotFoundError

class TaskInstanceService:
  def __init__(self, task_instance_repo: TaskInstanceRepository, task_repo: TaskRepository,
               task_schedule_repo: TaskScheduleRepository):
    self.task_instance_repo = task_instance_repo
    self.task_repo = task_repo
    self.task_schedule_repo = task_schedule_repo

  def create_task_instance(self, task_id, task_schedule_id, user_id):
    task = self._get_owned_task_or_raise(task_id=task_id, user_id=user_id)
    task_schedule = self._get_owned_task_schedule_or_raise(task_schedule_id=task_schedule_id, user_id=user_id)

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

    return self.task_instance_repo.create_task_instance(task_instance)

  def list_task_instances_by_date(self, user_id, date_instance: date):
    return self.task_instance_repo.list_task_instances_by_user_id_and_date(user_id=user_id, date_instance = date_instance)

  def complete_task_instance(
      self,
      task_instance_id:int,
      user_id,
      completion_level: str
  ):
    task_instance = self._get_owned_task_instance_or_raise(task_instance_id=task_instance_id, user_id=user_id)

    snapshot = task_instance.scoring_snapshot_json or {}
    if completion_level not in snapshot:
      raise ValueError("Invalid completion level")

    old_score = task_instance.score_awarded
    new_score = int(snapshot[completion_level])
    delta = new_score - old_score

    task_instance.status = TaskInstanceStatus.DONE.value
    task_instance.completion_level =completion_level
    task_instance.score_awarded = new_score

    updated_instance = self.task_instance_repo.update_task_instance(
      task_instance=task_instance
    )

    return {
      "task_instance": updated_instance,
      "delta": delta
    }

  def _get_owned_task_instance_or_raise(self, task_instance_id, user_id):
    task_instance = self.task_instance_repo.get_task_instance_by_id_and_user_id(task_instance_id, user_id)
    if not task_instance:
      raise NotFoundError("Task Instance not found")
    return task_instance


  def _get_owned_task_schedule_or_raise(self, task_schedule_id, user_id):
    task_schedule = self.task_schedule_repo.get_by_task_schedule_id_and_user_id(task_schedule_id, user_id)
    if not task_schedule:
      raise NotFoundError("Task Schedule not found")
    return task_schedule

  def _get_owned_task_or_raise(self, task_id, user_id):
    task = self.task_repo.get_by_task_id_and_user_id(task_id, user_id)
    if not task:
      raise NotFoundError("Task not found")
    return task