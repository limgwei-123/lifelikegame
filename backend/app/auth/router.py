from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.schemas import LoginRequest, SignupRequest, TokenResponse
from app.users.schemas import UserMeResponse

from app.auth.security import create_access_token
from app.auth.dependencies import get_auth_service
from app.auth.interfaces import AuthServiceInterface


router = APIRouter(prefix="/auth", tags=["auth"])

@router.post(
  "/signup",
  response_model=UserMeResponse,
  status_code=status.HTTP_201_CREATED
)
def signup(payload: SignupRequest, auth_service: AuthServiceInterface = Depends(get_auth_service)):

  user = auth_service.signup_user(
      email=payload.email,
      password=payload.password
    )

  return UserMeResponse(
    id=str(user.id),
    email=user.email
  )

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, auth_service: AuthServiceInterface = Depends(get_auth_service)):
  user = auth_service.authenticate_user(
    email=payload.email,
    password=payload.password
  )

  token = create_access_token(sub=str(user.id))

  return TokenResponse(
    access_token=token,
    token_type="bearer"
  )