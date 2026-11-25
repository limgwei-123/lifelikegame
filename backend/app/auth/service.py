
from app.auth.security import hash_password, verify_password
from uuid import UUID
from app.users.interfaces import UserServiceInterface
from app.errors.exception import ConflictError, PermissionDeniedError
class AuthService:

  def __init__(self, user_service: UserServiceInterface):
    self.user_service = user_service

  def signup_user(self, email: str, password: str):
    if self.user_service.is_email_registered(email):
      raise ConflictError("Email already registered")

    password_hash = hash_password(password)

    user = self.user_service.create_user(
      email=email,
      password_hash=password_hash
    )

    return user

  def authenticate_user(self, email: str, password: str):
    user = self.user_service.get_user_by_email(email)
    if not user:
      return None

    if not verify_password(password, user.password_hash):
      return None

    return user

  def change_password(self, user_id: str | UUID, auth_version: int, current_password: str, new_password: str) -> None:
    user = self.user_service.get_authenticated_user_for_update(user_id, auth_version)
    try:
      matches = verify_password(current_password, user.password_hash)
    except ValueError:
      matches = False
    if not matches:
      raise PermissionDeniedError('Current password is incorrect')
    self.user_service.update_password(user, hash_password(new_password))
