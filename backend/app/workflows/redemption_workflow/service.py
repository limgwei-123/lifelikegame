from app.rewards.interfaces import RewardServiceInterface
from app.redemptions.interfaces import RedemptionServiceInterface
from app.users.interfaces import UserServiceInterface
from app.point_ledgers.interfaces import PointLedgerServiceInterface

from app.shared.enums import RewardStatus
from app.rewards.schemas import UpdateRewardRequest
from app.point_ledgers.schemas import CreatePointLedgerRequest
from app.redemptions.schemas import CreateRedemptionRequest

from app.workflows.redemption_workflow.schemas import RedeemRewardResponse


from app.shared.function import get_scoring_scheme_workflow

class RedemptionWorkflowService:
  def __init__(self,
               reward_service: RewardServiceInterface,
               redemption_service: RedemptionServiceInterface,
               user_service: UserServiceInterface,
               point_ledger_service: PointLedgerServiceInterface):
    self.reward_service = reward_service
    self.redemption_service = redemption_service
    self.user_service = user_service
    self.point_ledger_service = point_ledger_service

  def redemption_workflow(self,reward_id, user_id):

    reward = self.reward_service.get_available_reward(reward_id=reward_id, user_id=user_id)
    user = self.user_service.get_user_by_id(user_id=user_id)

    if not reward:
      raise ValueError("There is no unclaimed reward")

    if reward.cost_points > user.current_value:
      raise ValueError("Not Enough Points")


    updated_user = self.user_service.update_user_point(user_id=user_id, delta=(-reward.cost_points))

    updated_reward = self.reward_service.update_reward(reward_id=reward_id, user_id=user_id, data=UpdateRewardRequest(status=RewardStatus.REDEEMED))

    redemption = self.redemption_service.create_redemption(
      user_id=user_id,
      payload=CreateRedemptionRequest(
        reward_id=reward_id
      )
    )
    point_ledger = self.point_ledger_service.create_point_ledger(user_id=user_id, payload=CreatePointLedgerRequest(
      delta=-reward.cost_points,
      entry_type="redeem",
      source_type="redemption",
      source_id=redemption.id,
    ))

    return RedeemRewardResponse(
      redemption_id=redemption.id,
      reward_id=reward.id,
      reward_title=reward.title,
      cost_points=reward.cost_points,
      remaining_points=user.current_value,
      redeemed_at=redemption.created_at
    )

