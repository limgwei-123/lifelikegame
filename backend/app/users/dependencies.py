from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.users.interfaces import UserServiceInterface
from app.users.repository import UserRepository
from app.users.service import UserService

def get_user_repository(
    db: Session = Depends(get_db)
)-> UserRepository:
  return UserRepository(db)

def get_user_service(
    user_repo: UserRepository = Depends(get_user_repository)
)->UserServiceInterface:
  return UserService(user_repo)