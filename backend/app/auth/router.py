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
  try:
    user = auth_service.signup_user(
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
def login(payload: LoginRequest, auth_service: AuthServiceInterface = Depends(get_auth_service)):
  user = auth_service.authenticate_user(
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