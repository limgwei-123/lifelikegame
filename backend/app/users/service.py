from sqlalchemy.orm import Session
from app.users.models import User
from app.users import repository as user_repository

def get_user_by_email(db: Session, email: str) -> User | None:
  return user_repository.get_user_by_email(db, email)

def get_user_by_id(db: Session, user_id: str) -> User | None:
  return user_repository.get_user_by_id(db, user_id)


def create_user(db: Session, email: str, password_hash: str) -> User:
  user = User(
    email = email,
    password_hash = password_hash
  )
  return user_repository.create_user(db, user)