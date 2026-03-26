from app.tasks.repository import TaskRepository
from app.goals.repository import GoalRepository
from app.tasks.schemas import CreateTaskRequest, UpdateTaskRequest

from app.shared.ownership import get_owned_goal_or_raise, get_owned_task_or_raise

class TaskService:
  def __init__(self, task_repo: TaskRepository, goal_repo: GoalRepository):
    self.task_repo = task_repo
    self.goal_repo = goal_repo


  def create_task(self, goal_id, user_id, payload: CreateTaskRequest):
    goal = get_owned_goal_or_raise(self.goal_repo,goal_id, user_id)
    data = payload.model_dump(exclude={"schedule"})
    data['user_id'] = goal.user_id
    data['goal_id'] = goal.id
    return self.task_repo.create(data)

  def list_tasks_by_goal_id(self, goal_id, user_id):
    goal = get_owned_goal_or_raise(self.goal_repo,goal_id = goal_id, user_id = user_id)
    return self.task_repo.list_by_goal_id(goal.id)

  def list_tasks_by_user_id(self, user_id):
    return self.task_repo.list_by_user_id(user_id)

  def get_task_by_id(self, task_id, user_id):
    get_owned_task_or_raise(self.task_repo,task_id, user_id)
    return self.task_repo.get_by_id(task_id)

  def update_task(self, task_id, user_id, data: UpdateTaskRequest):
    task = get_owned_task_or_raise(self.task_repo,task_id, user_id)

    return self.task_repo.update(
      task,
      data.model_dump(exclude_unset=True)
    )

  def delete_task(self, task_id, user_id):
    task = get_owned_task_or_raise(self.task_repo,task_id, user_id)

    self.task_repo.delete(task)
