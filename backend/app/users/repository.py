from sqlalchemy.orm import Session
from sqlalchemy import select

from app.users.models import User

def get_user_by_email(db: Session, email: str) -> User | None:
  result = db.execute(
    select(User).where(User.email == email)
  )
  return result.scalar_one_or_none()

def get_user_by_id(db: Session, user_id: str) -> User | None:
  return db.get(User, user_id)

def create_user(db: Session, user: User) -> User:

  db.add(user)
  db.commit()
  db.refresh(user)

  return user