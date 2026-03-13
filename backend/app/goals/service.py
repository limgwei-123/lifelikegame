from app.goals.repository import GoalRepository
from app.errors.exception import NotFoundError
class GoalService:
  def __init__(self, goal_repo: GoalRepository):
    self.goal_repo = goal_repo

  def _get_owned_goal_or_raise(self , goal_id, user_id):
    goal = self.goal_repo.get_by_gold_id_and_user_id(goal_id, user_id)
    if not goal:
      raise NotFoundError("Goal not found")
    return goal

  def create_goal(self,payload,user_id):
    return self.goal_repo.create_goal(payload, user_id)

  def get_goal_by_id(self, goal_id, user_id):
    self._get_owned_goal_or_raise(goal_id, user_id)
    return self.goal_repo.get_by_gold_id_and_user_id(goal_id, user_id)