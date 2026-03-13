from app.goals.repository import GoalRepository
from sqlalchemy.orm import Session

class GoalService:
  def __init__(self, goal_repo: GoalRepository):
    self.goal_repo = goal_repo

  def create_goal(self,payload,user_id):
    return self.goal_repo.create_goal(payload, user_id)

  def get_goal_by_id(self, goal_id, user_id):
    goal = self.goal_repo.get_goal_by_id(goal_id)

    if(goal.user_id != user_id):
      raise PermissionError("Not allowed to update this goal")

    return goal