from sqlalchemy.orm import Session
from app.goals.models import Goal

class GoalRepository:
  def __init__(self, db: Session):
    self.db = db

  def create(self, goal: Goal):
    self.db.add(goal)
    self.db.commit()
    self.db.refresh(goal)
    return goal

  def list(self, user_id):
    return self.db.query(Goal).filter(Goal.user_id == user_id).order_by(Goal.start_date.asc()).all()

  def get_by_id(self, goal_id):
    return self.db.query(Goal).filter(Goal.id == goal_id).first()

  def get_by_id_and_user_id(self, goal_id, user_id):
    return self.db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user_id).first()

  def update(self, goal: Goal) -> Goal:
    self.db.commit()
    self.db.refresh(goal)
    return goal

  def delete(self, goal: Goal):
    self.db.delete(goal)
    self.db.commit()