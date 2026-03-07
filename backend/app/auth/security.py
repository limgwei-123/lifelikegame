import os
import hashlib

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

def _sha256(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def hash_password(password: str) -> str:
  pre_hash = _sha256(password)
  print("DEBUG SHA256:", pre_hash, len(pre_hash))
  print(len(pwd_context.hash(pre_hash)))
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