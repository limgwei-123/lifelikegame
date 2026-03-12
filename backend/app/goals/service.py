from app.goals.repository import GoalRepository
from sqlalchemy.orm import Session

class GoalService:
  def __init__(self, goal_repo: GoalRepository):
    self.goal_repo = goal_repo

  def create_goal(self,payload,user_id):
    return self.goal_repo.create_goal(payload, user_id)