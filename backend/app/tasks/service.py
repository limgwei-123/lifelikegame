from app.tasks.repository import TaskRepository
from app.goals.repository import GoalRepository
from app.scoring_schemes.interfaces import ScoringSchemeServiceInterface

from app.tasks.schemas import CreateTaskRequest, UpdateTaskRequest

from app.shared.ownership import get_owned_goal_or_raise, get_owned_task_or_raise
from app.tasks.models import Task
from app.shared.function import get_scoring_scheme_workflow


class TaskService:
  def __init__(self, task_repo: TaskRepository, goal_repo: GoalRepository, scoring_scheme_service: ScoringSchemeServiceInterface):
    self.task_repo = task_repo
    self.goal_repo = goal_repo
    self.scoring_scheme_service = scoring_scheme_service


  def create_task(self, goal_id, user_id, payload: CreateTaskRequest):
    goal = get_owned_goal_or_raise(self.goal_repo,goal_id, user_id)

    scoring_scheme = get_scoring_scheme_workflow(scoring_scheme_id=payload.scoring_scheme_id,scoring_scheme_service=self.scoring_scheme_service)

    task = Task(
      title= payload.title,
      description=payload.description,
      is_active=payload.is_active,
      scoring_scheme_id=scoring_scheme.id,
      scoring_scheme_json=scoring_scheme.levels_json,
      is_scoring_scheme_locked=payload.is_scoring_scheme_locked,
      user_id=user_id,
      goal_id = goal.id
    )
    return self.task_repo.create(task)

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

    update_task = data.model_dump(exclude_unset=True)

    for field, value in update_task.items():
        setattr(task, field, value)

    return self.task_repo.update(
      task
    )

  def delete_task(self, task_id, user_id):
    task = get_owned_task_or_raise(self.task_repo,task_id, user_id)

    self.task_repo.delete(task)
