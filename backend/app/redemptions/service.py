from app.redemptions.repository import RedemptionRepository
from app.redemptions.schemas import CreateRedemptionRequest
from app.shared.ownership import get_owned_redemption_or_raise, get_owned_reward_or_raise

from app.rewards.repository import RewardRepository

class RedemptionService:
  def __init__(self, redemption_repo: RedemptionRepository, reward_repo: RewardRepository):
    self.redemption_repo = redemption_repo
    self.reward_repo = reward_repo

  def create_redemption(self, user_id, payload: CreateRedemptionRequest):
    data = payload.model_dump()
    data['user_id'] = user_id

    reward = get_owned_reward_or_raise(reward_repo= self.reward_repo, reward_id=data['reward_id'] , user_id=user_id)

    data['cost_points'] = reward.cost_points

    reward_snapshot = {
    "id": reward.id,
    "title": reward.title,
    "description": reward.description,
    "cost_points": reward.cost_points,
    }
    data['reward_snapshot_json'] = reward_snapshot
    data['reward_id'] = reward.id

    return self.redemption_repo.create(data)

  def list_redemptions_by_user_id(self, user_id):
    return self.redemption_repo.list_by_user_id(user_id=user_id)

  def get_redemption_by_id(self, redemption_id, user_id):
    return get_owned_redemption_or_raise(redemption_repo=self.redemption_repo, redemption_id=redemption_id, user_id=user_id)