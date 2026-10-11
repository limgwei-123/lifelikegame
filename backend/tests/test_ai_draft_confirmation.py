from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier, Event
from time import monotonic, sleep
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ai_usage_support import ai_user_ids
from app.ai_planner.draft_models import AIPlanDraft
from app.ai_planner.draft_repository import AIPlanDraftRepository
from app.ai_planner.draft_schemas import DraftPlan
from app.core.unit_of_work import build_unit_of_work
from app.errors.exception import AppError
from app.goals.models import Goal
from app.tasks.models import Task
from app.task_schedules.models import TaskSchedule
from app.task_instances.models import TaskInstance
from app.scoring_schemes.models import ScoringScheme
from test_ai_usage_service import authenticate


def make_draft(db, user_id, scheme_id=None):
    draft = AIPlanDraftRepository(db).create(user_id=user_id, plan=DraftPlan.model_validate({
        "goal_title": "Saved fitness", "tasks": [{"title": "Saved walk", "schedule_type": "daily",
            "schedule_value_json": {}, "scoring_scheme_id": scheme_id}],
    }))
    draft_id = draft.id
    db.commit()
    return draft_id


def counts(db, user_id):
    return [db.scalar(select(func.count()).select_from(model).where(model.user_id == user_id))
            for model in [Goal, Task, TaskSchedule, TaskInstance]]


@pytest.fixture
def confirmation_case(client, db):
    headers, user_id = authenticate(client)
    scheme = ScoringScheme(title="Draft scoring", levels_json={"normal": 2}, user_id=user_id)
    db.add(scheme)
    db.commit()
    scheme_id = scheme.id
    draft_id = make_draft(db, user_id, scheme_id)
    return headers, user_id, draft_id, scheme_id


def test_confirmation_uses_saved_plan_and_is_single_use(client, db, confirmation_case):
    headers, user_id, draft_id, scheme_id = confirmation_case
    response = client.post("/workflows/ai/confirm", headers=headers, json={"draft_id": str(draft_id)})
    assert response.status_code == 201, response.text
    assert response.json()["goal"]["title"] == "Saved fitness"
    task = response.json()["task_with_schedule_list"][0]["task"]
    assert task["title"] == "Saved walk"
    assert task["scoring_scheme_id"] == scheme_id
    assert task["scoring_scheme_json"] == {"normal": 2}
    assert task["user_id"] == str(user_id)
    db.expire_all()
    assert db.get(AIPlanDraft, draft_id).consumed_at is not None
    before = counts(db, user_id)
    repeated = client.post("/workflows/ai/confirm", headers=headers, json={"draft_id": str(draft_id)})
    assert repeated.status_code == 409, repeated.text
    assert repeated.json()["code"] == "AI_DRAFT_CONSUMED"
    assert counts(db, user_id) == before


@pytest.mark.parametrize("extra", [{"plan": {}}, {"user_id": str(uuid4())}])
def test_confirmation_forbids_payload_overrides(client, db, confirmation_case, extra):
    headers, user_id, draft_id, _ = confirmation_case
    before = counts(db, user_id)
    result = client.post("/workflows/ai/confirm", headers=headers, json={"draft_id": str(draft_id), **extra})
    assert result.status_code == 422, result.text
    assert counts(db, user_id) == before
    assert db.get(AIPlanDraft, draft_id).consumed_at is None


def test_unknown_foreign_and_anonymous_confirmation(client, db, confirmation_case):
    headers, user_id, draft_id, _ = confirmation_case
    other_headers, other_id = authenticate(client)
    foreign = client.post("/workflows/ai/confirm", headers=other_headers, json={"draft_id": str(draft_id)})
    unknown = client.post("/workflows/ai/confirm", headers=headers, json={"draft_id": str(uuid4())})
    assert foreign.status_code == unknown.status_code == 404
    assert foreign.json() == unknown.json()
    assert client.post("/workflows/ai/confirm", json={"draft_id": str(draft_id)}).status_code == 401
    assert counts(db, other_id) == [0, 0, 0, 0]


def test_confirmation_failure_rolls_back_records_and_draft_then_retry_succeeds(client, db, confirmation_case, monkeypatch):
    from app.tasks.service import TaskService
    headers, user_id, draft_id, _ = confirmation_case
    original = TaskService.create_task
    def fail(self, *args, **kwargs):
        original(self, *args, **kwargs)
        raise RuntimeError("after task insert")
    before = counts(db, user_id)
    with monkeypatch.context() as patch:
        patch.setattr(TaskService, "create_task", fail)
        with pytest.raises(RuntimeError, match="after task insert"):
            client.post("/workflows/ai/confirm", headers=headers, json={"draft_id": str(draft_id)})
    assert counts(db, user_id) == before
    assert db.get(AIPlanDraft, draft_id).consumed_at is None
    result = client.post("/workflows/ai/confirm", headers=headers, json={"draft_id": str(draft_id)})
    assert result.status_code == 201, result.text


def test_deleted_scoring_scheme_is_rechecked_at_confirm(client, db, confirmation_case):
    headers, user_id, draft_id, scheme_id = confirmation_case
    db.get(ScoringScheme, scheme_id).deleted_at = datetime.now(timezone.utc)
    db.commit()
    result = client.post("/workflows/ai/confirm", headers=headers, json={"draft_id": str(draft_id)})
    assert result.status_code == 404, result.text
    assert counts(db, user_id) == [0, 0, 0, 0]
    assert db.get(AIPlanDraft, draft_id).consumed_at is None


def test_corrupted_persisted_plan_is_rejected_without_domain_writes(client, db, confirmation_case):
    headers, user_id, draft_id, _ = confirmation_case
    db.get(AIPlanDraft, draft_id).plan_json = {"goal_title": "Bad", "tasks": []}
    db.commit()
    result = client.post("/workflows/ai/confirm", headers=headers, json={"draft_id": str(draft_id)})
    assert result.status_code == 422, result.text
    assert counts(db, user_id) == [0, 0, 0, 0]
    assert db.get(AIPlanDraft, draft_id).consumed_at is None


def test_concurrent_confirmation_creates_one_plan(db, ai_user_ids):
    from app.workflows.task_workflow.commands import ConfirmAiPlanCommand
    from app.workflows.task_workflow.dependencies import build_confirm_ai_plan_mediator
    user_id = ai_user_ids[0]
    scheme = ScoringScheme(title="Concurrent", levels_json={"normal": 1}, user_id=user_id)
    db.add(scheme)
    db.commit()
    draft_id = make_draft(db, user_id, scheme.id)
    barrier = Barrier(2)
    def confirm():
        with Session(db.get_bind()) as session:
            barrier.wait(timeout=10)
            try:
                build_confirm_ai_plan_mediator(session).send(ConfirmAiPlanCommand(
                    user_id=user_id, draft_id=draft_id,
                ))
                return "created"
            except AppError as error:
                return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: confirm(), range(2)))
    assert sorted(results) == ["AI_DRAFT_CONSUMED", "created"]
    db.expire_all()
    assert counts(db, user_id) == [1, 1, 1, 1]


def test_revision_waits_for_confirmation_and_rejects_consumed_source(db, ai_user_ids):
    from app.ai_planner.dependencies import build_ai_draft_service
    from app.workflows.task_workflow.commands import ConfirmAiPlanCommand
    from app.workflows.task_workflow.dependencies import build_confirm_ai_plan_mediator
    user_id = ai_user_ids[0]
    scheme = ScoringScheme(title="Race", levels_json={"normal": 1}, user_id=user_id)
    db.add(scheme)
    db.commit()
    draft_id = make_draft(db, user_id, scheme.id)
    started = Event()
    worker_pids = []
    edited_plan = DraftPlan.model_validate(db.get(AIPlanDraft, draft_id).plan_json)
    def revise():
        with Session(db.get_bind()) as session, build_unit_of_work(session).begin():
            worker_pids.append(session.scalar(text("SELECT pg_backend_pid()")))
            started.set()
            try:
                build_ai_draft_service(session).revise(user_id=user_id, draft_id=draft_id,
                    plan=edited_plan)
            except AppError as error:
                return error.code
    # The first transaction holds the row lock until its successful commit.
    with ThreadPoolExecutor(max_workers=1) as pool:
        with Session(db.get_bind()) as session:
            service = build_ai_draft_service(session)
            service.require_available(user_id=user_id, draft_id=draft_id, for_update=True)
            future = pool.submit(revise)
            assert started.wait(timeout=10)
            deadline = monotonic() + 10
            while not session.scalar(text("SELECT cardinality(pg_blocking_pids(:pid)) > 0"), {"pid": worker_pids[0]}):
                assert monotonic() < deadline, "Revision did not wait on the held draft row lock"
                sleep(0.01)
            build_confirm_ai_plan_mediator(session).send(ConfirmAiPlanCommand(
                user_id=user_id, draft_id=draft_id,
            ))
        assert future.result(timeout=10) == "AI_DRAFT_CONSUMED"


def test_saved_revision_remains_independently_confirmable(client, db, confirmation_case):
    headers, _, draft_id, _ = confirmation_case
    plan = db.get(AIPlanDraft, draft_id).plan_json
    revised = client.post(f"/ai-planner/drafts/{draft_id}/revisions", headers=headers, json=plan)
    assert revised.status_code == 201, revised.text
    for requested in [str(draft_id), revised.json()["draft_id"]]:
        result = client.post("/workflows/ai/confirm", headers=headers, json={"draft_id": requested})
        assert result.status_code == 201, result.text


def test_commit_failure_does_not_send_success_response(client, db, confirmation_case, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.unit_of_work import UnitOfWork
    headers, user_id, draft_id, _ = confirmation_case
    def fail_commit(self):
        raise RuntimeError("commit failed")
    monkeypatch.setattr(UnitOfWork, "commit", fail_commit)
    with TestClient(app, raise_server_exceptions=False) as observer:
        result = observer.post("/workflows/ai/confirm", headers=headers, json={"draft_id": str(draft_id)})
    assert result.status_code == 500, result.text
    assert counts(db, user_id) == [0, 0, 0, 0]
    assert db.get(AIPlanDraft, draft_id).consumed_at is None
