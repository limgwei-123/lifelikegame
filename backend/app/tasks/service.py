from app.tasks.repository import TaskRepository
from app.goals.interfaces import GoalServiceInterface
from app.scoring_schemes.interfaces import ScoringSchemeServiceInterface

from app.tasks.dtos import CreateTaskDTO, UpdateTaskDTO

from app.errors.exception import NotFoundError
from app.tasks.models import Task
from app.shared.function import get_scoring_scheme_workflow


class TaskService:
  def __init__(self, task_repo: TaskRepository, goal_service: GoalServiceInterface, scoring_scheme_service: ScoringSchemeServiceInterface):
    self.task_repo = task_repo
    self.goal_service = goal_service
    self.scoring_scheme_service = scoring_scheme_service


  def create_task(self, goal_id, user_id, payload: CreateTaskDTO):
    goal = self.goal_service.get_goal_by_id(goal_id=goal_id, user_id=user_id)

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
    goal = self.goal_service.get_goal_by_id(goal_id=goal_id, user_id=user_id)
    return self.task_repo.list_by_goal_id(goal.id)

  def list_tasks_by_user_id(self, user_id):
    return self.task_repo.list_by_user_id(user_id)

  def get_task_by_id(self, task_id, user_id):
    task = self.task_repo.get_by_id_and_user_id(task_id, user_id)
    if not task:
      raise NotFoundError("Task not found")
    return task

  def update_task(self, task_id, user_id, data: UpdateTaskDTO):
    task = self.get_task_by_id(task_id=task_id, user_id=user_id)

    for field, value in data.changes.items():
        setattr(task, field, value)

    return self.task_repo.update(
      task
    )

  def delete_task(self, task_id, user_id):
    task = self.get_task_by_id(task_id=task_id, user_id=user_id)

    self.task_repo.delete(task)
