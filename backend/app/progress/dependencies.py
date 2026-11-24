from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.progress.repository import ProgressRepository
from app.progress.service import ProgressService
from app.users.repository import UserRepository


def build_progress_service(db: Session) -> ProgressService:
    return ProgressService(ProgressRepository(db), UserRepository(db))


def get_progress_service(db: Session = Depends(get_db)) -> ProgressService:
    return build_progress_service(db)
