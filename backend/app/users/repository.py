from sqlalchemy.orm import Session
from sqlalchemy import select

from app.users.models import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_email(self, email: str) -> User | None:
        result = self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    def get_user_by_id(self, user_id: str) -> User | None:
        return self.db.get(User, user_id)

    def create_user(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user