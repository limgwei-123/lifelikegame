from copy import deepcopy
import json
from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ai_usage_support import ai_user_ids
from app.ai_planner.draft_models import AIPlanDraft
from app.users.models import User
from app.ai_planner.usage_models import AIDailyUsage
from test_ai_failures import sdk_transport
from test_ai_usage_service import authenticate, configure


PLAN = {"goal_title": "Fitness", "tasks": [{
    "title": "Walk", "schedule_type": "daily", "schedule_value_json": {},
}]}


@pytest.mark.parametrize("change", [
    {"tasks": []}, {"tasks": PLAN["tasks"] * 4}, {"goal_title": "  "},
    {"goal_title": "x" * 256}, {"user_id": "forged"},
])
def test_draft_plan_rejects_invalid_shape(change):
    from app.ai_planner.draft_schemas import DraftPlan
    with pytest.raises(ValidationError):
        DraftPlan.model_validate({**PLAN, **change})


@pytest.mark.parametrize("change", [
    {"title": " "}, {"title": "x" * 256}, {"scoring_scheme_json": {"normal": 999}},
    {"scoring_scheme_id": True}, {"scoring_scheme_id": "1"},
    {"schedule_type": "weekly", "schedule_value_json": {"days": []}},
    {"schedule_type": "weekly", "schedule_value_json": {"days": [7]}},
    {"schedule_type": "weekly", "schedule_value_json": {"days": [True]}},
    {"schedule_type": "weekly", "schedule_value_json": {"days": ["1"]}},
    {"schedule_type": "weekly", "schedule_value_json": {"days": [1], "extra": 1}},
    {"schedule_value_json": {"days": [1]}},
])
def test_draft_task_rejects_invalid_edits(change):
    from app.ai_planner.draft_schemas import DraftPlan
    with pytest.raises(ValidationError):
        DraftPlan.model_validate({**PLAN, "tasks": [{**PLAN["tasks"][0], **change}]})


def test_repository_roundtrip_ownership_and_flush_only(db, ai_user_ids):
    from app.ai_planner.draft_models import AIPlanDraft
    from app.ai_planner.draft_repository import AIPlanDraftRepository
    from app.ai_planner.draft_schemas import DraftPlan
    repo = AIPlanDraftRepository(db)
    before = deepcopy(PLAN)
    draft = repo.create(user_id=ai_user_ids[0], plan=DraftPlan.model_validate(PLAN))
    assert isinstance(draft.id, UUID)
    assert draft.created_at.utcoffset() is not None
    assert draft.consumed_at is None
    assert repo.get_owned(draft_id=draft.id, user_id=ai_user_ids[0]) is draft
    assert repo.get_owned(draft_id=draft.id, user_id=ai_user_ids[1]) is None
    assert draft.plan_json["goal_title"] == "Fitness"
    assert PLAN == before
    with Session(db.get_bind()) as observer:
        assert observer.get(AIPlanDraft, draft.id) is None
    draft_id = draft.id
    db.rollback()
    assert db.get(AIPlanDraft, draft_id) is None


def test_consumption_rolls_back_and_user_delete_cascades(db, ai_user_ids):
    from app.ai_planner.draft_models import AIPlanDraft
    from app.ai_planner.draft_repository import AIPlanDraftRepository
    from app.ai_planner.draft_schemas import DraftPlan
    repo = AIPlanDraftRepository(db)
    draft = repo.create(user_id=ai_user_ids[0], plan=DraftPlan.model_validate(PLAN))
    draft_id = draft.id
    db.commit()
    repo.consume(draft, consumed_at=datetime.now(timezone.utc))
    db.rollback()
    assert db.get(AIPlanDraft, draft_id).consumed_at is None
    db.execute(delete(User).where(User.id == ai_user_ids[0]))
    db.flush()
    assert db.scalar(select(AIPlanDraft.id).where(AIPlanDraft.id == draft_id)) is None


def test_generate_persists_owned_draft_and_revision_has_new_identity(client, db, sdk_transport, monkeypatch):
    configure(monkeypatch)
    headers, user_id = authenticate(client)
    sdk_transport[0].append(json.dumps({"status": "plan_ready", "message": "Ready", "plan": PLAN}))
    response = client.post("/ai-planner/generate-plan", headers=headers, json={"user_prompt": "Fitness"})
    assert response.status_code == 200, response.text
    draft_id = UUID(response.json()["draft_id"])
    draft = db.get(AIPlanDraft, draft_id)
    assert draft.user_id == user_id
    before = deepcopy(draft.plan_json)
    revision = client.post(f"/ai-planner/drafts/{draft_id}/revisions", headers=headers,
                           json={**PLAN, "goal_title": "Edited"})
    assert revision.status_code == 201, revision.text
    assert UUID(revision.json()["draft_id"]) != draft_id
    assert revision.json()["plan"]["goal_title"] == "Edited"
    db.expire_all()
    assert db.get(AIPlanDraft, draft_id).plan_json == before
    assert len(sdk_transport[1]) == 1
    assert db.scalar(select(AIDailyUsage.request_count).where(AIDailyUsage.user_id == user_id)) == 1


def test_need_more_info_has_no_draft(client, db, sdk_transport, monkeypatch):
    configure(monkeypatch)
    headers, user_id = authenticate(client)
    sdk_transport[0].append('{"status":"need_more_info","message":"When?"}')
    response = client.post("/ai-planner/generate-plan", headers=headers, json={"user_prompt": "Fitness"})
    assert response.status_code == 200, response.text
    assert response.json().get("draft_id") is None
    assert db.scalar(select(AIPlanDraft.id).where(AIPlanDraft.user_id == user_id)) is None


def test_draft_storage_failure_does_not_retry_ai_or_refund_quota(client, db, sdk_transport, monkeypatch):
    from app.ai_planner.draft_repository import AIPlanDraftRepository
    configure(monkeypatch)
    headers, user_id = authenticate(client)
    sdk_transport[0].append(json.dumps({"status": "plan_ready", "message": "Ready", "plan": PLAN}))
    def fail(*args, **kwargs):
        raise RuntimeError("storage failed")
    monkeypatch.setattr(AIPlanDraftRepository, "create", fail)
    with pytest.raises(RuntimeError, match="storage failed"):
        client.post("/ai-planner/generate-plan", headers=headers, json={"user_prompt": "Fitness"})
    assert len(sdk_transport[1]) == 1
    assert db.scalar(select(AIDailyUsage.request_count).where(AIDailyUsage.user_id == user_id)) == 1
    assert db.scalar(select(AIPlanDraft.id).where(AIPlanDraft.user_id == user_id)) is None


def test_revision_scoring_ownership_and_consumed_sources(client, db):
    from app.ai_planner.draft_repository import AIPlanDraftRepository
    from app.ai_planner.draft_schemas import DraftPlan
    from app.scoring_schemes.models import ScoringScheme
    from uuid import uuid4
    headers, user_id = authenticate(client)
    other_headers, other_id = authenticate(client)
    schemes = [ScoringScheme(title="own", levels_json={"normal": 1}, user_id=user_id),
               ScoringScheme(title="shared", levels_json={"normal": 1}, user_id=None),
               ScoringScheme(title="foreign", levels_json={"normal": 1}, user_id=other_id),
               ScoringScheme(title="deleted", levels_json={"normal": 1}, user_id=user_id,
                             deleted_at=datetime.now(timezone.utc))]
    db.add_all(schemes)
    source = AIPlanDraftRepository(db).create(user_id=user_id, plan=DraftPlan.model_validate(PLAN))
    source_id = source.id
    db.commit()
    for scheme, expected in zip(schemes, [201, 201, 404, 404]):
        edited = {**PLAN, "tasks": [{**PLAN["tasks"][0], "scoring_scheme_id": scheme.id}]}
        result = client.post(f"/ai-planner/drafts/{source_id}/revisions", headers=headers, json=edited)
        assert result.status_code == expected, result.text
    for requested_id, requested_headers in [(source_id, other_headers), (uuid4(), headers)]:
        result = client.post(f"/ai-planner/drafts/{requested_id}/revisions", headers=requested_headers, json=PLAN)
        assert result.status_code == 404, result.text
    source = db.get(AIPlanDraft, source_id)
    source.consumed_at = datetime.now(timezone.utc)
    db.commit()
    result = client.post(f"/ai-planner/drafts/{source_id}/revisions", headers=headers, json=PLAN)
    assert result.status_code == 409, result.text
    assert result.json()["code"] == "AI_DRAFT_CONSUMED"


def test_generated_draft_does_not_commit_auth_session(client, db, sdk_transport, monkeypatch):
    configure(monkeypatch)
    headers, user_id = authenticate(client)
    user = db.get(User, user_id)
    original = user.current_value
    user.current_value = (original or 0) + 1
    db.flush()
    sdk_transport[0].append(json.dumps({"status": "plan_ready", "message": "Ready", "plan": PLAN}))
    result = client.post("/ai-planner/generate-plan", headers=headers, json={"user_prompt": "Fitness"})
    assert result.status_code == 200, result.text
    draft_id = UUID(result.json()["draft_id"])
    with Session(db.get_bind()) as observer:
        assert observer.get(User, user_id).current_value == original
        assert observer.get(AIPlanDraft, draft_id) is not None
    db.rollback()
    assert db.get(User, user_id).current_value == original
    assert db.get(AIPlanDraft, draft_id) is not None


@pytest.mark.parametrize("count", [0, 4])
def test_revision_task_limit_rejects_before_writing(client, db, count):
    from ai_draft_support import save_draft
    headers, user_id = authenticate(client)
    draft_id = save_draft(db, user_id, PLAN)
    before = db.query(AIPlanDraft).filter_by(user_id=user_id).count()
    response = client.post(f"/ai-planner/drafts/{draft_id}/revisions", headers=headers,
                           json={**PLAN, "tasks": PLAN["tasks"] * count})
    assert response.status_code == 422, response.text
    assert response.json()["detail"][0]["loc"] == ["body", "tasks"]
    assert db.query(AIPlanDraft).filter_by(user_id=user_id).count() == before


def test_generation_commit_failure_never_returns_a_draft(client, db, sdk_transport, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.unit_of_work import UnitOfWork
    from app.ai_planner.draft_repository import AIPlanDraftRepository
    configure(monkeypatch)
    headers, user_id = authenticate(client)
    original_create = AIPlanDraftRepository.create
    original_commit = UnitOfWork.commit
    def create(self, **kwargs):
        result = original_create(self, **kwargs)
        self.db.info["fail_draft_commit"] = True
        return result
    def commit(self):
        if self.session.info.get("fail_draft_commit"):
            raise RuntimeError("draft commit failed")
        return original_commit(self)
    monkeypatch.setattr(AIPlanDraftRepository, "create", create)
    monkeypatch.setattr(UnitOfWork, "commit", commit)
    sdk_transport[0].append(json.dumps({"status": "plan_ready", "message": "Ready", "plan": PLAN}))
    with TestClient(app, raise_server_exceptions=False) as observer:
        response = observer.post("/ai-planner/generate-plan", headers=headers, json={"user_prompt": "Fitness"})
    assert response.status_code == 500, response.text
    assert len(sdk_transport[1]) == 1
    assert db.scalar(select(AIDailyUsage.request_count).where(AIDailyUsage.user_id == user_id)) == 1
    assert db.scalar(select(AIPlanDraft.id).where(AIPlanDraft.user_id == user_id)) is None
