from fastapi import APIRouter, Depends, HTTPException, status, Response

from app.auth.schemas import LoginRequest, SignupRequest, TokenResponse, ChangePasswordRequest
from app.users.schemas import UserMeResponse

from app.auth.security import create_access_token
from app.auth.dependencies import get_auth_service, get_account_auth_service
from app.auth.interfaces import AuthServiceInterface
from app.core.rate_limiting import limit_login, limit_signup, require_password_change


router = APIRouter(prefix="/auth", tags=["auth"])

@router.post(
  "/signup",
  response_model=UserMeResponse,
  status_code=status.HTTP_201_CREATED,
  dependencies=[Depends(limit_signup)],
)
def signup(payload: SignupRequest, auth_service: AuthServiceInterface = Depends(get_auth_service)):

  user = auth_service.signup_user(
      email=payload.email,
      password=payload.password
    )

  return UserMeResponse.model_validate(user)

@router.post("/login", response_model=TokenResponse, dependencies=[Depends(limit_login)])
def login(payload: LoginRequest, auth_service: AuthServiceInterface = Depends(get_auth_service)):
  user = auth_service.authenticate_user(
    email=payload.email,
    password=payload.password
  )

  if user is None:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

  token = create_access_token(sub=str(user.id), auth_version=user.auth_version)

  return TokenResponse(
    access_token=token,
    token_type="bearer"
  )


@router.post('/change-password', status_code=status.HTTP_204_NO_CONTENT)
def change_password(payload: ChangePasswordRequest, current_user=Depends(require_password_change),
                    auth_service: AuthServiceInterface = Depends(get_account_auth_service)):
  auth_service.change_password(current_user.id, current_user.auth_version,
                               payload.current_password.get_secret_value(), payload.new_password.get_secret_value())
  return Response(status_code=status.HTTP_204_NO_CONTENT)
