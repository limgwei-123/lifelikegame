from typing import Protocol
from app.users.models import User
import uuid

class UserServiceInterface(Protocol):

  def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
    ...

  def get_user_by_email(self, email: str) -> User | None:
    ...
  def update_user_point(self, user_id,delta):
    ...

  def create_user(self, email: str, password_hash: str) -> User:
    ...