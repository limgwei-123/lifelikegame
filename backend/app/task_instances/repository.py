from sqlalchemy.orm import Session

from app.task_instances.models import TaskInstance
from datetime import date
from app.tasks.models import Task
class TaskInstanceRepository:
  def __init__(self, db: Session):
    self.db = db

  def create(self, task_instance: TaskInstance):
    self.db.add(task_instance)
    self.db.commit()
    self.db.refresh(task_instance)
    return task_instance

  def list_by_task_id(self, task_id):
    return self.db.query(TaskInstance).filter(TaskInstance.task_id == task_id).order_by(TaskInstance.created_at.asc()).all()

  def list_by_user_id(self, user_id):
    return self.db.query(TaskInstance).filter(TaskInstance.user_id == user_id).order_by(TaskInstance.created_at.asc()).all()

  def get_by_task_id_and_date_instance(self, task_id, date_instance):
    return self.db.query(TaskInstance).filter(TaskInstance.task_id == task_id, TaskInstance.date_instance == date_instance).first()

  def list_by_user_id_between_date(self, user_id,start_date, end_date):

    return self.db.query(TaskInstance).filter(TaskInstance.user_id == user_id).filter(TaskInstance.date_instance >= start_date).filter(TaskInstance.date_instance <= end_date).order_by(TaskInstance.date_instance.asc()).all()



  def list_by_user_id_and_date(self, user_id, date_instance):
    return self.db.query(TaskInstance).filter(TaskInstance.user_id == user_id, TaskInstance.date_instance == date_instance).all()

  def get_by_id(self, task_instance_id):
    return self.db.query(TaskInstance).filter(TaskInstance.id == task_instance_id).first()

  def get_by_id_and_user_id(self, task_instance_id, user_id):
    return self.db.query(TaskInstance).filter(TaskInstance.id == task_instance_id, TaskInstance.user_id == user_id).first()


  def update(self, task_instance: TaskInstance) -> TaskInstance:

    self.db.commit()
    self.db.refresh(task_instance)
    return task_instance