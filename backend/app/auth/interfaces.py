from app.users.models import User
from typing import Protocol

class AuthServiceInterface(Protocol):
  def signup_user(self, email: str, password: str) -> User:
    pass

  def authenticate_user(self, email: str, password: str) -> User | None:
    pass