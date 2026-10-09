from app.rewards.dependencies import build_reward_service
from app.redemptions.dependencies import build_redemption_service
from app.users.dependencies import build_user_service
from app.point_ledgers.dependencies import build_point_ledger_service
from app.core.behaviors import LoggingBehavior, TransactionBehavior, ValidationBehavior, ValidatorRegistry
from app.core.mediator import HandlerRegistry, Mediator
from app.core.unit_of_work import build_unit_of_work
from app.workflows.redemption_workflow.commands import RedeemRewardCommand
from app.workflows.redemption_workflow.handlers import RedeemRewardCommandHandler
from app.workflows.redemption_workflow.validators import RedeemRewardCommandValidator


from app.workflows.redemption_workflow.interfaces import RedemptionWorkflowServiceInterface
from app.workflows.redemption_workflow.service import RedemptionWorkflowService
from fastapi import Depends
from sqlalchemy.orm import Session
from app.db import get_db, get_session

def build_redemption_workflow_service(db: Session)-> RedemptionWorkflowServiceInterface:
  return RedemptionWorkflowService(
    reward_service= build_reward_service(db),
    redemption_service= build_redemption_service(db),
    user_service = build_user_service(db),
    point_ledger_service = build_point_ledger_service(db),
  )

def get_redemption_workflow_service(
    db: Session = Depends(get_db),
) -> RedemptionWorkflowServiceInterface:
    return build_redemption_workflow_service(db)


def build_redeem_reward_mediator(db: Session) -> Mediator:
  handler_registry = HandlerRegistry()
  handler_registry.register(
    RedeemRewardCommand,
    RedeemRewardCommandHandler(build_redemption_workflow_service(db)),
  )

  validator_registry = ValidatorRegistry()
  validator_registry.register(RedeemRewardCommand, RedeemRewardCommandValidator())

  return Mediator(
    handler_registry,
    behaviors=[
      LoggingBehavior(),
      ValidationBehavior(validator_registry),
      TransactionBehavior(build_unit_of_work(db)),
    ],
  )


def get_redeem_reward_mediator(db: Session = Depends(get_session)) -> Mediator:
  return build_redeem_reward_mediator(db)
