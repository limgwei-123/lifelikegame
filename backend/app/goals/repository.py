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

  def get_by_gold_id_and_user_id(self, goal_id, user_id):
    return self.db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user_id).first()