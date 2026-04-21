from app.rewards.dependencies import build_reward_service
from app.redemptions.dependencies import build_redemption_service
from app.users.dependencies import build_user_service
from app.point_ledgers.dependencies import build_point_ledger_service


from app.workflows.redemption_workflow.interfaces import RedemptionWorkflowServiceInterface
from app.workflows.redemption_workflow.service import RedemptionWorkflowService
from fastapi import Depends
from sqlalchemy.orm import Session
from app.db import get_db

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