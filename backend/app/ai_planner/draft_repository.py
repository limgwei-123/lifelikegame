from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai_planner.draft_models import AIPlanDraft
from app.ai_planner.draft_schemas import DraftPlan


class AIPlanDraftRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, *, user_id: UUID, plan: DraftPlan) -> AIPlanDraft:
        draft = AIPlanDraft(user_id=user_id, plan_json=plan.model_dump(mode="json"))
        self.db.add(draft)
        self.db.flush()
        return draft

    def get_owned(self, *, draft_id: UUID, user_id: UUID, for_update: bool = False) -> AIPlanDraft | None:
        query = select(AIPlanDraft).where(AIPlanDraft.id == draft_id, AIPlanDraft.user_id == user_id)
        if for_update:
            query = query.with_for_update().execution_options(populate_existing=True)
        return self.db.scalar(query)

    def consume(self, draft: AIPlanDraft, *, consumed_at: datetime) -> None:
        draft.consumed_at = consumed_at
        self.db.flush()
