from app.users.models import User
from uuid import UUID
from app.users.repository import UserRepository
from app.users.schemas import UpdateProfileRequest
from app.errors.exception import AuthenticationError

class UserService:
  def __init__(self, user_repo: UserRepository):
    self.user_repo = user_repo

  def get_user_by_email(self, email: str) -> User | None:
    return self.user_repo.get_by_email(email)

  def is_email_registered(self, email: str) -> bool:
    return self.user_repo.is_email_registered(email)

  def get_user_by_id(self, user_id: str) -> User | None:
    return self.user_repo.get_by_id(user_id)

  def get_user_by_id_for_update(self, user_id: str) -> User | None:
    return self.user_repo.get_by_id_for_update(user_id)

  def get_authenticated_user_for_update(self, user_id: str | UUID, auth_version: int) -> User:
    user = self.user_repo.get_by_id_for_update(user_id)
    if user is None or user.auth_version != auth_version:
      raise AuthenticationError()
    return user

  def update_profile(self, user_id: str | UUID, auth_version: int, payload: UpdateProfileRequest) -> User:
    user = self.get_authenticated_user_for_update(user_id, auth_version)
    for field, value in payload.model_dump(exclude_unset=True).items():
      setattr(user, field, value)
    return self.user_repo.update(user)

  def update_password(self, user: User, password_hash: str) -> None:
    user.password_hash = password_hash
    user.auth_version += 1
    self.user_repo.update(user)

  def update_user_point(self, user_id,delta):
    return self.user_repo.update_user_point(user_id=user_id, delta=delta)


  def create_user(self,email: str, password_hash: str) -> User:
    user = User(
      email = email,
      password_hash = password_hash
    )
    return self.user_repo.create(user)
