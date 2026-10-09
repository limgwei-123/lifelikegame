from sqlalchemy.orm import Session
from app.goals.models import Goal
from datetime import datetime, timezone

class GoalRepository:
  def __init__(self, db: Session):
    self.db = db

  def create(self, goal: Goal):
    self.db.add(goal)
    self.db.flush()
    self.db.refresh(goal)
    return goal

  def list(self, user_id):
    return self._query().filter(Goal.user_id == user_id).order_by(Goal.start_date.asc()).all()

  def _query(self):
    return self.db.query(Goal).filter(Goal.deleted_at.is_(None))

  def get_by_id(self, goal_id):
    return self._query().filter(Goal.id == goal_id).first()

  def get_by_id_and_user_id(self, goal_id, user_id):
    return self._query().filter(Goal.id == goal_id, Goal.user_id == user_id).first()

  def update(self, goal: Goal) -> Goal:
    self.db.flush()
    self.db.refresh(goal)
    return goal

  def delete(self, goal: Goal):
    goal.deleted_at = datetime.now(timezone.utc)
    self.db.flush()
