from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.rewards.interfaces import RewardServiceInterface
from app.rewards.repository import RewardRepository
from app.rewards.service import RewardService


def build_reward_service(db: Session)->RewardServiceInterface:
  return RewardService(
    reward_repo=RewardRepository(db)
  )

def get_reward_service(db:Session = Depends(get_db))->RewardServiceInterface:
  return build_reward_service(db)