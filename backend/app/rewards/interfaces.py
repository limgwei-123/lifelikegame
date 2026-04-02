from typing import Protocol
from datetime import date

class RewardServiceInterface(Protocol):


  def create_reward(self, user_id, payload):
    ...

  def list_rewards_by_user_id(self, user_id):
    ...

  def get_reward_by_id(self, reward_id, user_id):
    ...

  def update_reward(self, reward_id, user_id, data):
    ...

  def delete_reward(self, reward_id, user_id):
    ...