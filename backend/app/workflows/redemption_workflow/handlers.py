from app.workflows.redemption_workflow.commands import RedeemRewardCommand
from app.workflows.redemption_workflow.dtos import RedeemRewardResultDTO
from app.workflows.redemption_workflow.interfaces import RedemptionWorkflowServiceInterface


class RedeemRewardCommandHandler:
  def __init__(self, redemption_workflow_service: RedemptionWorkflowServiceInterface):
    self._redemption_workflow_service = redemption_workflow_service

  def handle(self, command: RedeemRewardCommand) -> RedeemRewardResultDTO:
    return self._redemption_workflow_service.redemption_workflow(
      reward_id=command.reward_id,
      user_id=command.user_id,
    )
