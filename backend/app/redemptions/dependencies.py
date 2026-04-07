from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.redemptions.interfaces import RedemptionServiceInterface
from app.redemptions.repository import RedemptionRepository
from app.redemptions.service import RedemptionService

from app.rewards.repository import RewardRepository

def get_redemption_repository(db: Session = Depends(get_db))->RedemptionRepository:
  return RedemptionRepository(db)

def get_reward_repository(db: Session = Depends(get_db))->RewardRepository:
  return RewardRepository(db)

def get_redemption_service(redemption_repo: RedemptionRepository = Depends(get_redemption_repository), reward_repo: RewardRepository = Depends(get_reward_repository))->RedemptionServiceInterface:
  return RedemptionService(
    redemption_repo=redemption_repo,
    reward_repo=reward_repo
  )