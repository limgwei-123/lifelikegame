import hashlib

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

settings = get_settings()

JWT_SECRET = settings.jwt_secret.get_secret_value()
JWT_ALG = settings.jwt_alg
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

def _sha256(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def hash_password(password: str) -> str:
  pre_hash = _sha256(password)
  return pwd_context.hash(pre_hash)

def verify_password(password: str, password_hash: str) -> bool:
  pre_hash = _sha256(password)
  return pwd_context.verify(pre_hash, password_hash)

def create_access_token(sub: str, expire_minutes: Optional[int] = None) -> str:
  minutes = expire_minutes or ACCESS_TOKEN_EXPIRE_MINUTES
  now = datetime.now(timezone.utc)
  exp = now +timedelta(minutes=minutes)

  payload = {
    "sub": sub,
    "iat": int(now.timestamp()),
    "exp": int(exp.timestamp()),
  }

  return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def decode_token(token:str) -> dict:
  return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
