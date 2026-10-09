from app.rewards.models import Reward
from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.shared.enums import RewardStatus
class RewardRepository:
  def __init__(self, db:Session):
    self.db = db

  def create(self, reward: Reward):
    self.db.add(reward)
    self.db.flush()
    self.db.refresh(reward)
    return reward

  def list_by_user_id(self, user_id):
    return self._query().filter(Reward.user_id == user_id).all()

  def _query(self):
    return self.db.query(Reward).filter(Reward.deleted_at.is_(None))

  def get_by_id(self, reward_id):
    return self._query().filter(Reward.id == reward_id).first()

  def get_by_id_and_user_id(self, reward_id, user_id):
    return self._query().filter(Reward.id == reward_id, Reward.user_id == user_id).first()

  def get_available_reward_by_id_and_user_id(self, reward_id, user_id):
    return self._query().filter(Reward.id == reward_id, Reward.user_id == user_id, Reward.status == RewardStatus.AVAILABLE).first()

  def get_by_id_and_user_id_for_update(self, reward_id, user_id):
    return (self._query()
            .filter(Reward.id == reward_id, Reward.user_id == user_id)
            .populate_existing().with_for_update().first())

  def update(self, reward: Reward):

    self.db.flush()
    self.db.refresh(reward)
    return reward

  def delete(self, reward: Reward):
    reward.deleted_at = datetime.now(timezone.utc)
    self.db.flush()
