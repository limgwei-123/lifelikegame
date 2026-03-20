from app.tasks.interfaces import TaskServiceInterface
from app.task_schedules.interfaces import TaskScheduleServiceInterface

from app.errors.exception import NotFoundError
from app.tasks.schemas import CreateTaskRequest


class TaskWorkflowService:
  def __init__(self, task_schedule_service: TaskScheduleServiceInterface, task_service: TaskServiceInterface):
    self.task_schedule_service = task_schedule_service
    self.task_service = task_service

  def create_task_with_schedule(self, goal_id, user_id, payload: CreateTaskRequest):
    task = self.task_service.create_task(
      goal_id=goal_id,
      user_id=user_id,
      payload=payload
      )

    schedule = None

    if payload.schedule:
      schedule = self.task_schedule_service.create_task_schedule(
        task_id= task.id,
        user_id=user_id,
        payload=payload.schedule
      )

      task.schedule = schedule

    return {
      "task": task,
      "schedule": schedule
    }


