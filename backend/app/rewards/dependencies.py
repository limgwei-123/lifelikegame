from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.rewards.interfaces import RewardServiceInterface
from app.rewards.repository import RewardRepository
from app.rewards.service import RewardService

def get_reward_repository(db: Session = Depends(get_db))->RewardRepository:
  return RewardRepository(db)

def get_reward_service(reward_repo: RewardRepository = Depends(get_reward_repository))->RewardServiceInterface:
  return RewardService(
    reward_repo=reward_repo
  )