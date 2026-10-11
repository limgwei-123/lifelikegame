from datetime import date
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.ai_planner.usage_models import AIDailyUsage


class AIUsageRepository:
    def __init__(self, session: Session):
        self.session = session

    def try_consume(self, user_id: UUID, usage_date: date, limit: int) -> bool:
        if limit <= 0:
            raise ValueError("AI daily limit must be positive")
        statement = insert(AIDailyUsage).values(
            user_id=user_id, usage_date=usage_date, request_count=1,
        ).on_conflict_do_update(
            index_elements=[AIDailyUsage.user_id, AIDailyUsage.usage_date],
            set_={"request_count": AIDailyUsage.request_count + 1},
            where=AIDailyUsage.request_count < limit,
        ).returning(AIDailyUsage.request_count)
        return self.session.execute(statement).scalar_one_or_none() is not None
