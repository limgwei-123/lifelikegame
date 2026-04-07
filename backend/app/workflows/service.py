from app.tasks.interfaces import TaskServiceInterface
from app.task_schedules.interfaces import TaskScheduleServiceInterface
from app.goals.interfaces import GoalServiceInterface

from app.workflows.schemas import CreateTaskWithScheduleRequest, TaskWithScheduleResponse

class WorkflowService:
  def __init__(self, goal_service: GoalServiceInterface, task_service: TaskServiceInterface, task_schedule_service: TaskScheduleServiceInterface):
    self.goal_service = goal_service
    self.task_service = task_service
    self.task_schedule_service = task_schedule_service

  def create_task_with_schedule(self, goal_id, user_id, payload: CreateTaskWithScheduleRequest):
    task = self.task_service.create_task(
      goal_id=goal_id,
      user_id=user_id,
      payload=payload.task
      )

    schedule = None

    if payload.schedule:
      schedule = self.task_schedule_service.create_task_schedule(
        task_id= task.id,
        user_id=user_id,
        payload=payload.schedule
      )

      task.schedule = schedule

    return TaskWithScheduleResponse(
      task=task,
      schedule=schedule
    )
