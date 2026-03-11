from fastapi import APIRouter, Depends
from app.users.schemas import (
  UserMeResponse
)
from app.auth.deps import get_current_user
from app.db import get_db
from app.users.models import User

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/me", response_model=UserMeResponse)
def me(current_user: User = Depends(get_current_user)):
  return current_user