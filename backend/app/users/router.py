from fastapi import APIRouter, Depends
from uuid import UUID
from app.users.schemas import (
  UserMeResponse
)
from app.auth.dependencies import get_current_user

from app.errors.exception import NotFoundError

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserMeResponse)
def me(current_user: UserMeResponse = Depends(get_current_user)):
  return current_user

@router.get("/{user_id}", response_model=UserMeResponse)
def get_user(user_id: UUID, current_user = Depends(get_current_user)):
  if user_id != current_user.id:
    raise NotFoundError("User not found")
  return current_user
