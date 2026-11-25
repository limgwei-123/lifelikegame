from sqlalchemy.orm import Session

from app.task_instances.models import TaskInstance
from datetime import date
from app.tasks.models import Task
from app.task_schedules.models import TaskSchedule
from app.task_schedules.recurrence import MANAGED_RECURRENCE
from app.progress.models import TaskCompletion
from sqlalchemy import or_
class TaskInstanceRepository:
  def __init__(self, db: Session):
    self.db = db

  def create(self, task_instance: TaskInstance):
    self.db.add(task_instance)
    self.db.flush()
    self.db.refresh(task_instance)
    return task_instance

  def list_by_task_id(self, task_id):
    return self._query().filter(TaskInstance.task_id == task_id).order_by(TaskInstance.created_at.asc()).all()

  def pending_for_task(self, task_id):
    return self._query().filter(TaskInstance.task_id == task_id, TaskInstance.status == 'todo').order_by(
      TaskInstance.date_instance, TaskInstance.id).all()

  def has_managed_history(self, task_id):
    return self.db.query(TaskInstance.id).filter(TaskInstance.task_id == task_id,
      TaskInstance.generated_reason == MANAGED_RECURRENCE).first() is not None

  def latest_completed_date(self, task_id):
    row = self.db.query(TaskInstance.date_instance).filter(TaskInstance.task_id == task_id,
      TaskInstance.status == 'done').order_by(TaskInstance.date_instance.desc()).first()
    return row[0] if row else None

  def latest_managed_completion_time(self, task_id):
    row = self.db.query(TaskCompletion.completed_at).join(TaskInstance,
      TaskInstance.id == TaskCompletion.task_instance_id).filter(TaskInstance.task_id == task_id,
      TaskInstance.generated_reason == MANAGED_RECURRENCE).order_by(TaskCompletion.completed_at.desc()).first()
    return row[0] if row else None

  def pending_for_user(self, user_id):
    return self._query().join(Task, Task.id == TaskInstance.task_id).join(
      TaskSchedule, TaskSchedule.id == TaskInstance.task_schedule_id).filter(
        TaskInstance.user_id == user_id, Task.user_id == user_id, TaskSchedule.user_id == user_id,
        TaskInstance.status == 'todo', Task.is_active.is_(True),
        or_(TaskSchedule.deleted_at.is_(None), TaskInstance.generated_reason == MANAGED_RECURRENCE),
        TaskSchedule.task_id == Task.id, Task.deleted_at.is_(None),
      ).order_by(TaskInstance.date_instance, TaskInstance.id).all()

  def _query(self):
    return self.db.query(TaskInstance).filter(TaskInstance.deleted_at.is_(None))

  def list_by_user_id(self, user_id):
    return self._query().filter(TaskInstance.user_id == user_id).order_by(TaskInstance.created_at.asc()).all()

  def get_by_task_id_and_date_instance(self, task_id, date_instance):
    return self._query().filter(TaskInstance.task_id == task_id, TaskInstance.date_instance == date_instance).first()

  def list_by_user_id_between_date(self, user_id,start_date, end_date):

    return self._query().filter(TaskInstance.user_id == user_id).filter(TaskInstance.date_instance >= start_date).filter(TaskInstance.date_instance <= end_date).order_by(TaskInstance.date_instance.asc()).all()



  def list_by_user_id_and_date(self, user_id, date_instance):
    return self._query().filter(TaskInstance.user_id == user_id, TaskInstance.date_instance == date_instance).all()

  def get_by_id(self, task_instance_id):
    return self._query().filter(TaskInstance.id == task_instance_id).first()

  def get_by_id_and_user_id(self, task_instance_id, user_id):
    return self._query().filter(TaskInstance.id == task_instance_id, TaskInstance.user_id == user_id).first()

  def get_by_id_and_user_id_for_update(self, task_instance_id, user_id):
    return (
      self._query()
      .filter(
        TaskInstance.id == task_instance_id,
        TaskInstance.user_id == user_id,
      )
      .with_for_update()
      .populate_existing()
      .first()
    )


  def update(self, task_instance: TaskInstance) -> TaskInstance:

    self.db.flush()
    self.db.refresh(task_instance)
    return task_instance
