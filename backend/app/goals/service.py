from app.goals.repository import GoalRepository
from app.goals.schemas import CreateGoalRequest,UpdateGoalRequest
from app.errors.exception import NotFoundError
from app.goals.models import Goal
from app.users.interfaces import UserServiceInterface
from app.shared.dates import player_today

class GoalService:
  def __init__(self, goal_repo: GoalRepository, user_service: UserServiceInterface):
    self.goal_repo = goal_repo
    self.user_service = user_service

  def create_goal(self,user_id, payload:CreateGoalRequest):
    start_date = payload.start_date
    if start_date is None:
      user = self.user_service.get_user_by_id(user_id)
      if user is None:
        raise NotFoundError('User not found')
      start_date = player_today(user.timezone)
    goal = Goal(
      title=payload.title,
      start_date=start_date,
      target_date=payload.target_date,
      current_value=payload.current_value,
      target_value=payload.target_value,
      user_id=user_id
    )

    return self.goal_repo.create(goal)

  def list_goals(self, user_id):
    return self.goal_repo.list(user_id)

  def get_goal_by_id(self, goal_id, user_id):
    goal = self.goal_repo.get_by_id_and_user_id(goal_id, user_id)
    if not goal:
      raise NotFoundError("Goal not found")
    return goal


  def update_goal(self, goal_id, user_id, data: UpdateGoalRequest):
    goal = self.get_goal_by_id(goal_id=goal_id, user_id=user_id)

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(goal, field, value)

    return self.goal_repo.update(goal)

  def delete_goal(self, goal_id, user_id):
    goal = self.get_goal_by_id(goal_id=goal_id, user_id=user_id)

    self.goal_repo.delete(goal)
