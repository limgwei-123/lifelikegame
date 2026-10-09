from typing import Protocol
from app.users.models import User

class UserServiceInterface(Protocol):

  def get_user_by_id(self, user_id: str) -> User | None:
    ...

  def get_user_by_id_for_update(self, user_id: str) -> User | None:
    ...

  def get_user_by_email(self, email: str) -> User | None:
    ...

  def is_email_registered(self, email: str) -> bool:
    ...
  def update_user_point(self, user_id: str, delta: int) -> User:
    ...

  def create_user(self, email: str, password_hash: str) -> User:
    ...
