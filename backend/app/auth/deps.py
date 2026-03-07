from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth.security import decode_token
from app.db import get_db
from app.users.models import User
from app.users.service import get_user_by_id

bearer_scheme = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db:Session = Depends(get_db),
)->User:
  token = credentials.credentials

  try:
    payload = decode_token(token)
    user_id = payload.get("sub")

    if not user_id:
      raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token"
      )

  except JWTError:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail= "Invalid token",
    )

  user = get_user_by_id(db, user_id)

  if not user:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="User not found",
    )

  return user