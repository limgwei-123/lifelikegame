from sqlalchemy.orm import Session

from app.task_instances.models import TaskInstance

class TaskInstanceRepository:
  def __init__(self, db: Session):
    self.db = db

  def create_task_instance(self, data):
    task_instance = TaskInstance(**data)
    self.db.add(task_instance)
    self.db.commit()
    self.db.refresh(task_instance)
    return task_instance

  def list_task_instances_by_task_id(self, task_id):
    return self.db.query(TaskInstance).filter(TaskInstance.task_id == task_id).order_by(TaskInstance.created_at.asc()).all()

  def list_task_instances_by_user_id(self, user_id):
    return self.db.query(TaskInstance).filter(TaskInstance.user_id == user_id).order_by(TaskInstance.created_at.asc()).all()

  def list_task_instances_by_user_id_and_date(self, user_id, date_instance):
    return self.db.query(TaskInstance).filter(TaskInstance.user_id == user_id, TaskInstance.date_instance == date_instance).all()

  def get_task_instance_by_id(self, task_instance_id):
    return self.db.query(TaskInstance).filter(TaskInstance.id == task_instance_id).first()

  def get_task_instance_by_id_and_user_id(self, task_instance_id, user_id):
    return self.db.query(TaskInstance).filter(TaskInstance.id == task_instance_id, TaskInstance.user_id == user_id).first()


  def update_task_instance(self, task_instance: TaskInstance) -> TaskInstance:

    self.db.commit()
    self.db.refresh(task_instance)
    return task_instance