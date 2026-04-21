from app.rewards.models import Reward
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.shared.enums import RewardStatus
class RewardRepository:
  def __init__(self, db:Session):
    self.db = db

  def create(self, reward: Reward):
    self.db.add(reward)
    self.db.commit()
    self.db.refresh(reward)
    return reward

  def list_by_user_id(self, user_id):
    return self.db.query(Reward).filter(Reward.user_id == user_id).all()

  def get_by_id_and_user_id(self, reward_id, user_id):
    return self.db.query(Reward).filter(Reward.id == reward_id, Reward.user_id == user_id).first()

  def get_available_reward_by_id_and_user_id(self, reward_id, user_id):
    return self.db.query(Reward).filter(Reward.id == reward_id, Reward.user_id == user_id, Reward.status == RewardStatus.AVAILABLE).first()

  def update(self, reward: Reward):

    self.db.commit()
    self.db.refresh(reward)
    return reward

  def delete(self, reward: Reward):
    self.db.delete(reward)
    self.db.commit()