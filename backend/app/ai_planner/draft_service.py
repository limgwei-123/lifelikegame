from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import ValidationError

from app.ai_planner.draft_models import AIPlanDraft
from app.ai_planner.draft_repository import AIPlanDraftRepository
from app.ai_planner.draft_schemas import DraftPlan, DraftResponse
from app.ai_planner.errors import AIDraftConsumedError, AIInvalidOutputError
from app.ai_planner.providers.base import GeneratedPlan
from app.errors.exception import NotFoundError, RequestValidationError
from app.scoring_schemes.interfaces import ScoringSchemeServiceInterface

if TYPE_CHECKING:
    from app.workflows.task_workflow.interfaces import TaskWorkflowServiceInterface
    from app.workflows.task_workflow.schemas import GoalTaskSchduleResponse


class AIPlanDraftService:
    def __init__(self, repository: AIPlanDraftRepository, scoring_scheme_service: ScoringSchemeServiceInterface):
        self.repository = repository
        self.scoring_scheme_service = scoring_scheme_service

    def validate_plan(self, *, user_id: UUID, plan: DraftPlan) -> DraftPlan:
        plan = DraftPlan.model_validate(plan.model_dump())
        for task in plan.tasks:
            if task.scoring_scheme_id is not None:
                self.scoring_scheme_service.get_usable_scoring_scheme_by_id(task.scoring_scheme_id, user_id)
        return plan

    def save_generated(self, *, user_id: UUID, plan: GeneratedPlan) -> DraftResponse:
        try:
            validated = DraftPlan.model_validate(plan.model_dump())
        except ValidationError as exc:
            raise AIInvalidOutputError() from exc
        draft = self.repository.create(user_id=user_id, plan=validated)
        return DraftResponse(draft_id=draft.id, plan=validated)

    def require_available(self, *, user_id: UUID, draft_id: UUID, for_update: bool = False) -> AIPlanDraft:
        draft = self.repository.get_owned(draft_id=draft_id, user_id=user_id, for_update=for_update)
        if draft is None:
            raise NotFoundError("AI draft not found")
        if draft.consumed_at is not None:
            raise AIDraftConsumedError()
        return draft

    def revise(self, *, user_id: UUID, draft_id: UUID, plan: DraftPlan) -> DraftResponse:
        self.require_available(user_id=user_id, draft_id=draft_id, for_update=True)
        validated = self.validate_plan(user_id=user_id, plan=plan)
        draft = self.repository.create(user_id=user_id, plan=validated)
        return DraftResponse(draft_id=draft.id, plan=validated)

    def confirm(self, *, user_id: UUID, draft_id: UUID,
                task_workflow_service: "TaskWorkflowServiceInterface") -> "GoalTaskSchduleResponse":
        draft = self.require_available(user_id=user_id, draft_id=draft_id, for_update=True)
        try:
            plan = DraftPlan.model_validate(draft.plan_json)
        except ValidationError as exc:
            raise RequestValidationError([{
                "field": "draft_id", "message": "Saved AI draft is invalid", "code": "invalid_draft",
            }]) from exc
        plan = self.validate_plan(user_id=user_id, plan=plan)
        result = task_workflow_service.create_from_ai_plan(user_id=user_id, plan=plan)
        self.repository.consume(draft, consumed_at=datetime.now(timezone.utc))
        return result
