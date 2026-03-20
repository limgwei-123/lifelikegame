from app.tasks.repository import TaskRepository
from app.task_schedules.repository import TaskScheduleRepository
from app.task_schedules.schemas import CreateTaskScheduleRequest, UpdateTaskScheduleRequest

from app.errors.exception import NotFoundError

class TaskScheduleService:
  def __init__(self, task_schedule_repo: TaskScheduleRepository, task_repo: TaskRepository):
    self.task_schedule_repo = task_schedule_repo
    self.task_repo = task_repo


  def create_task_schedule(self, task_id, user_id, payload: CreateTaskScheduleRequest):
    task = self._get_owned_task_or_raise(task_id, user_id)
    data = payload.model_dump()
    data['user_id'] = task.user_id
    data['task_id'] = task.id
    return self.task_schedule_repo.create_task_schedule(data)

  def list_task_schedules_by_task_id(self, task_id, user_id):
    task = self._get_owned_task_or_raise(task_id = task_id, user_id = user_id)
    return self.task_schedule_repo.list_task_schedules_by_task_id(task.id)

  def list_task_schedules_by_user_id(self, user_id):
    return self.task_schedule_repo.list_task_schedules_by_user_id(user_id)

  def get_task_schedule_by_id(self, task_schedule_id, user_id):
    self._get_owned_task_schedule_or_raise(task_schedule_id, user_id)
    return self.task_schedule_repo.get_task_schedule_by_id(task_schedule_id)

  def update_task_schedule(self, task_schedule_id, user_id, data: UpdateTaskScheduleRequest):
    task_schedule = self._get_owned_task_schedule_or_raise(task_schedule_id, user_id)

    return self.task_schedule_repo.update_task_schedule(
      task_schedule,
      data.model_dump(exclude_unset=True)
    )

  def delete_task_schedule(self, task_schedule_id, user_id):
    task_schedule = self._get_owned_task_schedule_or_raise(task_schedule_id, user_id)

    self.task_schedule_repo.delete_task_schedule(task_schedule)

  def _get_owned_task_schedule_or_raise(self, task_schedule_id, user_id):
    task_schedule = self.task_schedule_repo.get_by_task_schedule_id_and_user_id(task_schedule_id, user_id)
    if not task_schedule:
      raise NotFoundError("Task Schedule not found")
    return task_schedule

  def _get_owned_task_or_raise(self , task_id, user_id):
    task = self.task_repo.get_by_task_id_and_user_id(task_id, user_id)
    if not task:
      raise NotFoundError("Task not found")
    return task