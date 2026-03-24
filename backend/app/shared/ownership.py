from app.errors.exception import NotFoundError
from app.goals.repository import GoalRepository
from app.tasks.repository import TaskRepository
from app.task_schedules.repository import TaskScheduleRepository
from app.task_instances.repository import TaskInstanceRepository


def get_owned_goal_or_raise(goal_repo:GoalRepository , goal_id, user_id):
  goal = goal_repo.get_by_goal_id_and_user_id(goal_id, user_id)
  if not goal:
    raise NotFoundError("Goal not found")
  return goal


def get_owned_task_or_raise(task_repo: TaskRepository, task_id, user_id):
  task = task_repo.get_by_task_id_and_user_id(task_id, user_id)
  if not task:
    raise NotFoundError("Task not found")
  return task


def get_owned_task_schedule_or_raise(task_schedule_repo: TaskScheduleRepository, task_schedule_id, user_id):
  task_schedule = task_schedule_repo.get_by_task_schedule_id_and_user_id(task_schedule_id, user_id)
  if not task_schedule:
    raise NotFoundError("Task Schedule not found")
  return task_schedule

def get_owned_task_instance_or_raise(task_instance_repo: TaskInstanceRepository, task_instance_id, user_id):
  task_instance = task_instance_repo.get_task_instance_by_id_and_user_id(task_instance_id, user_id)
  if not task_instance:
    raise NotFoundError("Task Instance not found")
  return task_instance


