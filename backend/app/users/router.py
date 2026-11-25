from fastapi import APIRouter, Depends
from uuid import UUID
from app.users.schemas import (
  UserMeResponse, UpdateProfileRequest
)
from app.auth.dependencies import get_current_user
from app.users.dependencies import get_account_user_service
from app.users.interfaces import UserServiceInterface

from app.errors.exception import NotFoundError

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserMeResponse)
def me(current_user: UserMeResponse = Depends(get_current_user)):
  return current_user


@router.patch('/me', response_model=UserMeResponse)
def update_me(payload: UpdateProfileRequest, current_user=Depends(get_current_user),
              user_service: UserServiceInterface = Depends(get_account_user_service)):
  return user_service.update_profile(current_user.id, current_user.auth_version, payload)

@router.get("/{user_id}", response_model=UserMeResponse)
def get_user(user_id: UUID, current_user = Depends(get_current_user)):
  if user_id != current_user.id:
    raise NotFoundError("User not found")
  return current_user
