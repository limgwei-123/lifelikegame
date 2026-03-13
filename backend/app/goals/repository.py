from sqlalchemy.orm import Session
from app.goals.models import Goal

class GoalRepository:
  def __init__(self, db: Session):
    self.db = db

  def create_goal(self, payload, user_id):
    goal_data = payload.model_dump()
    goal_data['user_id'] = user_id
    goal = Goal(**goal_data)
    self.db.add(goal)
    self.db.commit()
    self.db.refresh(goal)
    return goal

  def get_goal_by_id(self, id):
    return self.db.get(Goal, id)