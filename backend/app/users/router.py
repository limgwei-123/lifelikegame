from fastapi import APIRouter, Depends, HTTPException
from app.users.schemas import (
  UserMeResponse
)
from app.auth.dependencies import get_current_user

from app.users.dependencies import get_user_service
from app.users.interfaces import UserServiceInterface

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserMeResponse)
def me(current_user: UserMeResponse = Depends(get_current_user)):
  return current_user

@router.get("/{user_id}")
def get_user(user_id: str, user_service: UserServiceInterface = Depends(get_user_service)):
  user = user_service.get_user_by_id(user_id)

  if not user:
    raise HTTPException(status_code=404, detail="User not found")

  return user