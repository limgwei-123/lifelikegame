from app.users.models import User
from typing import Protocol
from uuid import UUID

class AuthServiceInterface(Protocol):
  def signup_user(self, email: str, password: str) -> User:
    pass

  def authenticate_user(self, email: str, password: str) -> User | None:
    pass

  def change_password(self, user_id: str | UUID, auth_version: int, current_password: str, new_password: str) -> None:
    ...
