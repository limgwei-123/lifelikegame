from app.task_schedules.models import TaskSchedule

from sqlalchemy.orm import Session

class TaskScheduleRepository:
  def __init__(self, db: Session):
    self.db = db

  def create(self, data):
    task_schedule = TaskSchedule(**data)
    self.db.add(task_schedule)
    self.db.commit()
    self.db.refresh(task_schedule)
    return task_schedule

  def list_all(self):
    return self.db.query(TaskSchedule).all()

  def list_by_task_id(self, task_id):
    return self.db.query(TaskSchedule).filter(TaskSchedule.task_id == task_id).order_by(TaskSchedule.created_at.asc()).all()

  def list_by_user_id(self, user_id):
    return self.db.query(TaskSchedule).filter(TaskSchedule.user_id == user_id).order_by(TaskSchedule.created_at.asc()).all()

  def get_by_id(self, task_schedule_id):
    return self.db.query(TaskSchedule).filter(TaskSchedule.id == task_schedule_id).first()

  def get_by_id_and_user_id(self, task_schedule_id, user_id):
    return self.db.query(TaskSchedule).filter(TaskSchedule.id == task_schedule_id, TaskSchedule.user_id == user_id).first()

  def update(self, task_schedule: TaskSchedule, data: dict) -> TaskSchedule:
    for key, value in data.items():
      setattr(task_schedule, key, value)

    self.db.commit()
    self.db.refresh(task_schedule)
    return task_schedule

  def delete(self, task_schedule: TaskSchedule):
    self.db.delete(task_schedule)
    self.db.commit()

