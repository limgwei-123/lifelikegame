from app.task_schedules.models import TaskSchedule

from sqlalchemy.orm import Session

class TaskScheduleRepository:
  def __init__(self, db: Session):
    self.db = db

  def create_task_schedule(self, data):
    task_schedule = TaskSchedule(**data)
    self.db.add(task_schedule)
    self.db.commit()
    self.db.refresh(task_schedule)
    return task_schedule

  def list_task_schedules_by_task_id(self, task_id):
    return self.db.query(TaskSchedule).filter(TaskSchedule.task_id == task_id).order_by(TaskSchedule.created_at.asc()).all()

  def list_task_schedules_by_user_id(self, user_id):
    return self.db.query(TaskSchedule).filter(TaskSchedule.user_id == user_id).order_by(TaskSchedule.created_at.asc()).all()

  def get_task_schedule_by_id(self, task_schedule_id):
    return self.db.query(TaskSchedule).filter(TaskSchedule.id == task_schedule_id).first()

  def get_by_task_schedule_id_and_user_id(self, task_schedule_id, user_id):
    return self.db.query(TaskSchedule).filter(TaskSchedule.id == task_schedule_id, TaskSchedule.user_id == user_id).first()

  def update_task_schedule(self, task_schedule: TaskSchedule, data: dict) -> TaskSchedule:
    for key, value in data.items():
      setattr(task_schedule, key, value)

    self.db.commit()
    self.db.refresh(task_schedule)
    return task_schedule

  def delete_task_schedule(self, task_schedule: TaskSchedule):
    self.db.delete(task_schedule)
    self.db.commit()

