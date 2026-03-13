
from app.auth.security import hash_password, verify_password
from app.users.interfaces import UserServiceInterface
from app.errors.exception import ConflictError
class AuthService:

  def __init__(self, user_service: UserServiceInterface):
    self.user_service = user_service

  def signup_user(self, email: str, password: str):
    existing_user = self.user_service.get_user_by_email(email)
    if existing_user:
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