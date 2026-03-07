from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.schemas import (
  LoginRequest,
  SignupRequest,
  TokenResponse,
  UserMeResponse
)

from app.auth.security import create_access_token
from app.auth.service import authenticate_user, signup_user
from app.db import get_db
from app.users.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post(
  "/signup",
  response_model=UserMeResponse,
  status_code=status.HTTP_201_CREATED
)
def signup(payload: SignupRequest, db:Session = Depends(get_db)):
  try:
    user = signup_user(
      db=db,
      email=payload.email,
      password=payload.password
    )
  except ValueError as e:
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail=str(e),
    )

  return UserMeResponse(
    id=str(user.id),
    email=user.email
  )

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
  user = authenticate_user(
    db=db,
    email=payload.email,
    password=payload.password
  )

  if not user:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Invalid credentials"
    )

  token = create_access_token(sub=str(user.id))

  return TokenResponse(
    access_token=token,
    token_type="bearer"
  )

@router.get("/me", response_model=UserMeResponse)
def me(current_user: User = Depends(get_current_user)):
  return UserMeResponse(
    id = str(current_user.id),
    email=current_user.email
  )