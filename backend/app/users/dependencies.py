from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.users.interfaces import UserServiceInterface
from app.users.repository import UserRepository
from app.users.service import UserService


def build_user_service(db: Session) -> UserServiceInterface:
    return UserService(
        user_repo=UserRepository(db),
    )

def get_user_service(db: Session = Depends(get_db))->UserServiceInterface:
  return build_user_service(db)