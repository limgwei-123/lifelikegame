from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_user
from app.redemptions.schemas import CreateRedemptionRequest, RedemptionResponse
from app.redemptions.interfaces import RedemptionServiceInterface
from app.redemptions.dependencies import get_redemption_service

router = APIRouter(prefix="/redemptions", tags=["redemptions"])

@router.post('',response_model=RedemptionResponse, status_code=status.HTTP_201_CREATED)
def create_redemption(payload: CreateRedemptionRequest,current_user = Depends(get_current_user), redemption_service: RedemptionServiceInterface = Depends(get_redemption_service)):
  return redemption_service.create_redemption(payload=payload, user_id=current_user.id)


@router.get("", response_model=list[RedemptionResponse], status_code=status.HTTP_200_OK)
def list_redemptions_by_user_id(current_user = Depends(get_current_user), redemption_service: RedemptionServiceInterface = Depends(get_redemption_service)):
  return redemption_service.list_redemptions_by_user_id(user_id=current_user.id)

@router.get('/{redemption_id}', response_model= RedemptionResponse, status_code= status.HTTP_200_OK)
def get_redemption_by_id(redemption_id,
                   current_user = Depends(get_current_user),
                   redemption_service: RedemptionServiceInterface = Depends(get_redemption_service)):
  return redemption_service.get_redemption_by_id(redemption_id= redemption_id, user_id= current_user.id)