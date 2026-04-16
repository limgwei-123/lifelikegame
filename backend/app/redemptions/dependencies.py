from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.redemptions.interfaces import RedemptionServiceInterface
from app.redemptions.repository import RedemptionRepository
from app.redemptions.service import RedemptionService

from app.rewards.repository import RewardRepository

def build_redemption_service(db:Session)->RedemptionServiceInterface:
  return RedemptionService(
    redemption_repo=RedemptionRepository(db),
    reward_repo=RewardRepository(db)
  )

def get_redemption_service(db: Session = Depends(get_db))->RedemptionServiceInterface:
  return build_redemption_service(db)