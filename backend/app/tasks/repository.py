from app.tasks.models import Task
from app.goals.models import Goal
from app.users.models import User
from datetime import datetime, timezone

from sqlalchemy.orm import Session

class TaskRepository:
  def __init__(self, db: Session):
    self.db = db

  def create(self, task: Task):
    self.db.add(task)
    self.db.flush()
    self.db.refresh(task)
    return task

  def list_by_goal_id(self, goal_id):
    return self._query().filter(Task.goal_id == goal_id).order_by(Task.created_at.asc()).all()

  def _query(self):
    return self.db.query(Task).filter(
      Task.deleted_at.is_(None),
      Task.goal.has(Goal.deleted_at.is_(None)),
      Task.user.has(User.deleted_at.is_(None)),
    )

  def list_by_user_id(self, user_id):
    return self._query().filter(Task.user_id == user_id).order_by(Task.created_at.asc()).all()

  def get_by_id(self, task_id):
    return self._query().filter(Task.id == task_id).first()

  def get_by_id_and_user_id(self, task_id, user_id):
    return self._query().filter(Task.id == task_id, Task.user_id == user_id).first()

  def update(self, task: Task) -> Task:
    self.db.flush()
    self.db.refresh(task)
    return task

  def delete(self, task: Task):
    task.deleted_at = datetime.now(timezone.utc)
    self.db.flush()

