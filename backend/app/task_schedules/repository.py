from app.task_schedules.models import TaskSchedule
from app.tasks.models import Task
from app.goals.models import Goal
from app.users.models import User
from datetime import datetime, timezone
from sqlalchemy import and_

from sqlalchemy.orm import Session

class TaskScheduleRepository:
  def __init__(self, db: Session):
    self.db = db

  def create(self, task_schedule:TaskSchedule):
    self.db.add(task_schedule)
    self.db.flush()
    self.db.refresh(task_schedule)
    return task_schedule

  def list_all(self):
    return self._query().all()

  def list_for_generation(self):
    return self._query().filter(
      TaskSchedule.task.has(Task.is_active.is_(True)),
    ).all()

  def _query(self):
    return self.db.query(TaskSchedule).filter(
      TaskSchedule.deleted_at.is_(None),
      TaskSchedule.task.has(and_(
        Task.deleted_at.is_(None),
        Task.goal.has(Goal.deleted_at.is_(None)),
        Task.user.has(User.deleted_at.is_(None)),
      )),
    )

  def list_by_task_id(self, task_id):
    return self._query().filter(TaskSchedule.task_id == task_id).order_by(TaskSchedule.created_at.asc()).all()

  def list_by_user_id(self, user_id):
    return self._query().filter(TaskSchedule.user_id == user_id).order_by(TaskSchedule.created_at.asc()).all()

  def get_by_id(self, task_schedule_id):
    return self._query().filter(TaskSchedule.id == task_schedule_id).first()

  def get_by_id_and_user_id(self, task_schedule_id, user_id):
    return self._query().filter(TaskSchedule.id == task_schedule_id, TaskSchedule.user_id == user_id).first()

  def update(self, task_schedule: TaskSchedule) -> TaskSchedule:
    self.db.flush()
    self.db.refresh(task_schedule)
    return task_schedule

  def delete(self, task_schedule: TaskSchedule):
    task_schedule.deleted_at = datetime.now(timezone.utc)
    self.db.flush()

