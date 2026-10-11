from sqlalchemy.orm import Session

from app.ai_planner.usage_record_models import AIUsageRecord


class AIUsageRecordRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, record: AIUsageRecord) -> None:
        self.session.add(record)
        self.session.flush()
