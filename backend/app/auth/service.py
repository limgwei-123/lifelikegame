from sqlalchemy.orm import Session

from app.auth.security import hash_password, verify_password
from app.users.service import get_user_by_email, create_user

def signup_user(db: Session, email: str, password: str):
  existing_user = get_user_by_email(db, email)
  if existing_user:
    raise ValueError("Email already registered")

  password_hash = hash_password(password)

  user = create_user(
    db=db,
    email=email,
    password_hash=password_hash
  )

  return user

def authenticate_user(db: Session, email: str, password: str):
  user = get_user_by_email(db, email)
  if not user:
    return None

  if not verify_password(password, user.password_hash):
    return None

  return user