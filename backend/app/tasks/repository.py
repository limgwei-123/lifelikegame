from app.tasks.models import Task

from sqlalchemy.orm import Session

class TaskRepository:
  def __init__(self, db: Session):
    self.db = db

  def create_task(self, data):
    task = Task(**data)
    self.db.add(task)
    self.db.commit()
    self.db.refresh(task)
    return task

  def list_tasks_by_goal_id(self, goal_id):
    return self.db.query(Task).filter(Task.goal_id == goal_id).order_by(Task.created_at.asc()).all()

  def list_tasks_by_user_id(self, user_id):
    return self.db.query(Task).filter(Task.user_id == user_id).order_by(Task.created_at.asc()).all()

  def get_by_task_id(self, task_id):
    return self.db.query(Task).filter(Task.id == task_id).first()

  def get_by_task_id_and_user_id(self, task_id, user_id):
    return self.db.query(Task).filter(Task.id == task_id, Task.user_id == user_id).first()

  def update_task(self, task: Task, data: dict) -> Task:
    for key, value in data.items():
      setattr(task, key, value)

    self.db.commit()
    self.db.refresh(task)
    return task

  def delete_task(self, task: Task):
    self.db.delete(task)
    self.db.commit()

