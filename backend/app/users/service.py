from app.users.models import User
from app.users.repository import UserRepository

class UserService:
  def __init__(self, user_repo: UserRepository):
    self.user_repo = user_repo

  def get_user_by_email(self, email: str) -> User | None:
    return self.user_repo.get_user_by_email(email)

  def get_user_by_id(self, user_id: str) -> User | None:
    return self.user_repo.get_user_by_id(user_id)


  def create_user(self,email: str, password_hash: str) -> User:
    user = User(
      email = email,
      password_hash = password_hash
    )
    return self.user_repo.create_user(user)