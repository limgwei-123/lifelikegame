from app.rewards.repository import RewardRepository
from app.rewards.schemas import CreateRewardRequest, UpdateRewardRequest
from app.shared.ownership import get_owned_reward_or_raise

from app.rewards.models import Reward

class RewardService:
  def __init__(self, reward_repo: RewardRepository):
    self.reward_repo = reward_repo

  def create_reward(self, user_id, payload: CreateRewardRequest):
    reward = Reward(
      title = payload.title,
      description = payload.description,
      cost_points = payload.cost_points,
      user_id = user_id
    )

    return self.reward_repo.create(reward)

  def list_rewards_by_user_id(self, user_id):
    return self.reward_repo.list_by_user_id(user_id=user_id)

  def get_reward_by_id(self, reward_id, user_id):
    return get_owned_reward_or_raise(reward_repo=self.reward_repo, reward_id=reward_id, user_id=user_id)

  def get_available_reward(self, reward_id, user_id):
    return self.reward_repo.get_available_reward_by_id_and_user_id(reward_id=reward_id, user_id=user_id)

  def update_reward(self, reward_id, user_id, data: UpdateRewardRequest):
    reward = get_owned_reward_or_raise(reward_repo=self.reward_repo, reward_id=reward_id, user_id=user_id)

    update_reward = data.model_dump(exclude_unset=True)

    for field, value in update_reward.items():
        setattr(reward, field, value)


    return self.reward_repo.update(
      reward=reward,
    )

  def delete_reward(self, reward_id, user_id):
    reward = get_owned_reward_or_raise(reward_repo=self.reward_repo, reward_id=reward_id, user_id=user_id)

    self.reward_repo.delete(reward=reward)