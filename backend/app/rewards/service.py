from app.rewards.repository import RewardRepository
from app.rewards.schemas import CreateRewardRequest, UpdateRewardRequest
from app.shared.ownership import get_owned_reward_or_raise

class RewardService:
  def __init__(self, reward_repo: RewardRepository):
    self.reward_repo = reward_repo

  def create_reward(self, user_id, payload: CreateRewardRequest):
    data = payload.model_dump()
    data['user_id'] = user_id
    return self.reward_repo.create(data)

  def list_rewards_by_user_id(self, user_id):
    return self.reward_repo.list_by_user_id(user_id=user_id)

  def get_reward_by_id(self, reward_id, user_id):
    return get_owned_reward_or_raise(reward_repo=self.reward_repo, reward_id=reward_id, user_id=user_id)

  def update_reward(self, reward_id, user_id, data: UpdateRewardRequest):
    reward = get_owned_reward_or_raise(reward_repo=self.reward_repo, reward_id=reward_id, user_id=user_id)

    return self.reward_repo.update(
      reward=reward,
      data=data.model_dump(exclude_unset=True)
    )

  def delete_reward(self, reward_id, user_id):
    reward = get_owned_reward_or_raise(reward_repo=self.reward_repo, reward_id=reward_id, user_id=user_id)

    self.reward_repo.delete(reward=reward)