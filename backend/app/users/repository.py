from sqlalchemy.orm import Session
from sqlalchemy import select

from app.users.models import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        result = self.db.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    def get_by_id(self, user_id: str) -> User | None:
        return self.db.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        ).scalar_one_or_none()

    def is_email_registered(self, email: str) -> bool:
        # Deleted accounts retain their email reservation, but cannot log in.
        return self.db.query(User.id).filter(User.email == email).first() is not None

    def get_by_id_for_update(self, user_id: str) -> User | None:
        return self.db.execute(
            select(User)
            .where(User.id == user_id, User.deleted_at.is_(None))
            .with_for_update()
            .execution_options(populate_existing=True)
        ).scalar_one_or_none()

    def update_user_point(self, user_id, delta):
        self.db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).update(
        {User.current_value: User.current_value + delta}
        )
        self.db.flush()
        user = self.get_by_id(user_id)
        return user

    def update(self, user: User):
        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)
        return user

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)
        return user
