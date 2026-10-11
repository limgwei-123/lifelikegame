from app.ai_planner.draft_repository import AIPlanDraftRepository
from app.ai_planner.draft_schemas import DraftPlan


def save_draft(db, user_id, plan):
    draft = AIPlanDraftRepository(db).create(user_id=user_id, plan=DraftPlan.model_validate(plan))
    draft_id = str(draft.id)
    db.commit()
    return draft_id
