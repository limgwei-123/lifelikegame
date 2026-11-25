from typing import Protocol
from uuid import UUID
from app.users.models import User
from app.users.schemas import UpdateProfileRequest

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

  def get_authenticated_user_for_update(self, user_id: str | UUID, auth_version: int) -> User:
    ...

  def update_profile(self, user_id: str | UUID, auth_version: int, payload: UpdateProfileRequest) -> User:
    ...

  def update_password(self, user: User, password_hash: str) -> None:
    ...
