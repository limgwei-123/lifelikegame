from typing import Protocol
from datetime import date
from app.rewards.models import Reward
from app.rewards.schemas import UpdateRewardRequest

class RewardServiceInterface(Protocol):


  def create_reward(self, user_id, payload):
    ...

  def list_rewards_by_user_id(self, user_id):
    ...

  def get_reward_by_id(self, reward_id, user_id)->Reward:
    ...

  def get_available_reward(self, reward_id, user_id)->Reward:
    ...

  def update_reward(self, reward_id, user_id, data: UpdateRewardRequest):
    ...

  def delete_reward(self, reward_id, user_id):
    ...