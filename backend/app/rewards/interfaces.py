from typing import Protocol
import uuid
from app.rewards.models import Reward
from app.rewards.schemas import CreateRewardRequest, UpdateRewardRequest

class RewardServiceInterface(Protocol):


  def create_reward(self, user_id: uuid.UUID, payload: CreateRewardRequest) -> Reward:
    ...

  def list_rewards_by_user_id(self, user_id: uuid.UUID) -> list[Reward]:
    ...

  def get_reward_by_id(self, reward_id: int, user_id: uuid.UUID) -> Reward:
    ...

  def get_reward_by_id_for_update(self, reward_id: int, user_id: uuid.UUID) -> Reward:
    ...

  def get_available_reward(self, reward_id: int, user_id: uuid.UUID) -> Reward:
    ...

  def update_reward(self, reward_id: int, user_id: uuid.UUID, data: UpdateRewardRequest) -> Reward:
    ...

  def delete_reward(self, reward_id: int, user_id: uuid.UUID) -> None:
    ...
