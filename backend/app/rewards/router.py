from fastapi import APIRouter, Depends, status, Query

from app.auth.dependencies import get_current_user
from app.rewards.schemas import CreateRewardRequest, UpdateRewardRequest, RewardResponse
from app.rewards.interfaces import RewardServiceInterface
from app.rewards.dependencies import get_reward_service

router = APIRouter(prefix="/rewards", tags=["rewards"])

@router.post('',response_model=RewardResponse, status_code=status.HTTP_201_CREATED)
def create_reward(payload: CreateRewardRequest,current_user = Depends(get_current_user), reward_service: RewardServiceInterface = Depends(get_reward_service)):
  return reward_service.create_reward(payload=payload, user_id=current_user.id)


@router.get("", response_model=list[RewardResponse], status_code=status.HTTP_200_OK)
def list_rewards_by_user_id(current_user = Depends(get_current_user), reward_service: RewardServiceInterface = Depends(get_reward_service)):
  return reward_service.list_rewards_by_user_id(user_id=current_user.id)

@router.get('/{reward_id}', response_model= RewardResponse, status_code= status.HTTP_200_OK)
def get_reward_by_id(reward_id,
                   current_user = Depends(get_current_user),
                   reward_service: RewardServiceInterface = Depends(get_reward_service)):
  return reward_service.get_reward_by_id(reward_id= reward_id, user_id= current_user.id)

@router.post('/{reward_id}', response_model= RewardResponse, status_code= status.HTTP_200_OK)
def update_reward(reward_id,
                payload: UpdateRewardRequest,
                current_user = Depends(get_current_user),
                reward_service: RewardServiceInterface = Depends(get_reward_service)):
  return reward_service.update_reward(
    reward_id= reward_id,
    user_id= current_user.id,
    data= payload
  )

@router.post("/{reward_id}/delete", status_code = status.HTTP_204_NO_CONTENT)
def delete_reward(
  reward_id,
  current_user = Depends(get_current_user),
  reward_service: RewardServiceInterface = Depends(get_reward_service)
):
  reward_service.delete_reward(reward_id=reward_id, user_id=current_user.id)