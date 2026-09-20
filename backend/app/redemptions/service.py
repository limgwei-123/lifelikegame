from app.redemptions.repository import RedemptionRepository
from app.redemptions.schemas import CreateRedemptionRequest
from app.errors.exception import NotFoundError

from app.rewards.interfaces import RewardServiceInterface
from app.redemptions.models import Redemption

class RedemptionService:
  def __init__(self, redemption_repo: RedemptionRepository, reward_service: RewardServiceInterface):
    self.redemption_repo = redemption_repo
    self.reward_service = reward_service

  def create_redemption(self, user_id, payload: CreateRedemptionRequest):

    reward = self.reward_service.get_reward_by_id(reward_id=payload.reward_id, user_id=user_id)

    reward_snapshot_json = {
    "id": reward.id,
    "title": reward.title,
    "description": reward.description,
    "cost_points": reward.cost_points,
    }

    redemption = Redemption(
      reward_id = reward.id,
      reward_snapshot_json = reward_snapshot_json,
      cost_points = reward.cost_points,
      user_id = user_id
    )
    return self.redemption_repo.create(redemption)

  def list_redemptions_by_user_id(self, user_id):
    return self.redemption_repo.list_by_user_id(user_id=user_id)

  def get_redemption_by_id(self, redemption_id, user_id):
    redemption = self.redemption_repo.get_by_id_and_user_id(redemption_id=redemption_id, user_id=user_id)
    if not redemption:
      raise NotFoundError("Redemption not found")
    return redemption
