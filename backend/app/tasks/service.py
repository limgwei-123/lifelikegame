from app.tasks.repository import TaskRepository
from app.goals.repository import GoalRepository
from app.tasks.schemas import CreateTaskRequest, UpdateTaskRequest
from app.errors.exception import NotFoundError

class TaskService:
  def __init__(self, task_repo: TaskRepository, goal_repo: GoalRepository):
    self.task_repo = task_repo
    self.goal_repo = goal_repo


  def create_task(self, goal_id, user_id, payload: CreateTaskRequest):
    goal = self.goal_repo.get_by_goal_id_and_user_id(goal_id, user_id)
    data = payload.model_dump()
    data['user_id'] = goal.user_id
    data['goal_id'] = goal.id
    return self.task_repo.create_task(data)

  def list_tasks_by_goal_id(self, goal_id, user_id):
    goal = self._get_owned_goal_or_raise(goal_id = goal_id, user_id = user_id)
    return self.task_repo.list_tasks_by_goal_id(goal.id)

  def list_tasks_by_user_id(self, user_id):
    return self.task_repo.list_tasks_by_user_id(user_id)

  def get_task_by_id(self, task_id, user_id):
    self._get_owned_task_or_raise(task_id, user_id)
    return self.task_repo.get_by_task_id(task_id)

  def update_task(self, task_id, user_id, data: UpdateTaskRequest):
    task = self._get_owned_task_or_raise(task_id, user_id)

    return self.task_repo.update_task(
      task,
      data.model_dump(exclude_unset=True)
    )

  def delete_task(self, task_id, user_id):
    task = self._get_owned_task_or_raise(task_id, user_id)

    self.task_repo.delete_task(task)

  def _get_owned_task_or_raise(self, task_id, user_id):
    task = self.task_repo.get_by_task_id_and_user_id(task_id, user_id)
    if not task:
      raise NotFoundError("Task not found")
    return task

  def _get_owned_goal_or_raise(self , goal_id, user_id):
    goal = self.goal_repo.get_by_goal_id_and_user_id(goal_id, user_id)
    if not goal:
      raise NotFoundError("Goal not found")
    return goal