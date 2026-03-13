from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError

from app.auth.security import decode_token
from app.auth.interfaces import AuthServiceInterface
from app.auth.service import AuthService

from app.users.dependencies import get_user_service
from app.users.interfaces import UserServiceInterface
from app.users.models import User

bearer_scheme = HTTPBearer()

def _unauthorized(detail: str = "Unauthorized") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
    )

def get_auth_service(
    user_service: UserServiceInterface = Depends(get_user_service)
)-> AuthServiceInterface:
  return AuthService(user_service)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    user_service: UserServiceInterface = Depends(get_user_service),
)->User:
  token = credentials.credentials

  try:
    payload = decode_token(token)
    user_id = payload.get("sub")

    if not user_id:
      raise _unauthorized("Invalid token")

  except JWTError:
    raise _unauthorized("Invalid token")

  user = user_service.get_user_by_id(user_id)

  if not user:
    raise _unauthorized("Invalid token")

  return user