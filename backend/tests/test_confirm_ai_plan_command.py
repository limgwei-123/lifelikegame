import logging
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ai_draft_support import save_draft
from app.ai_planner.draft_models import AIPlanDraft
from app.auth.security import create_access_token
from app.errors.exception import AppError, NotFoundError, RequestValidationError
from app.goals.models import Goal
from app.scoring_schemes.models import ScoringScheme
from app.task_instances.models import TaskInstance
from app.task_schedules.models import TaskSchedule
from app.tasks.models import Task
from app.users.models import User


@pytest.fixture
def command_draft(db):
    user = User(email=f"confirm-command-{uuid4()}@example.com", password_hash="unused")
    db.add(user)
    db.flush()
    user_id = user.id
    scheme = ScoringScheme(title="Command scoring", levels_json={"normal": 2}, user_id=user_id)
    db.add(scheme)
    db.flush()
    draft_id = UUID(save_draft(db, user_id, {
        "goal_title": "Command goal",
        "tasks": [{"title": "Command task", "scoring_scheme_id": scheme.id,
                   "schedule_type": "daily", "schedule_value_json": {}}],
    }))
    db.rollback()
    return {"user_id": user_id, "draft_id": draft_id,
            "headers": {"Authorization": f"Bearer {create_access_token(sub=str(user_id))}"}}


def state(bind, case):
    with Session(bind) as reader:
        counts = [reader.scalar(select(func.count()).select_from(model).where(
            model.user_id == case["user_id"],
        )) for model in [Goal, Task, TaskSchedule, TaskInstance]]
        return counts, reader.get(AIPlanDraft, case["draft_id"]).consumed_at is not None


def test_confirmation_api_uses_command_pipeline_and_commits_once(client, db, command_draft, monkeypatch, caplog):
    commits = []
    original_commit = db.commit

    def commit():
        commits.append(True)
        original_commit()

    monkeypatch.setattr(db, "commit", commit)
    with caplog.at_level(logging.INFO, logger="app.cqrs"):
        response = client.post("/workflows/ai/confirm", headers=command_draft["headers"],
                               json={"draft_id": str(command_draft["draft_id"])})
    assert response.status_code == 201, response.text
    assert response.json()["goal"]["title"] == "Command goal"
    assert response.json()["task_with_schedule_list"][0]["task"]["user_id"] == str(command_draft["user_id"])
    assert commits == [True]
    assert state(db.get_bind(), command_draft) == ([1, 1, 1, 1], True)
    records = [record for record in caplog.records
               if getattr(record, "request_type", None) == "ConfirmAiPlanCommand"]
    assert len(records) == 1
    assert records[0].handler_type == "ConfirmAiPlanCommandHandler"
    assert records[0].transactional is True
    assert records[0].outcome == "success"
    assert records[0].request_id


def test_confirmation_command_commits_outside_http(db, command_draft):
    from app.workflows.task_workflow.commands import ConfirmAiPlanCommand
    from app.workflows.task_workflow.dependencies import build_confirm_ai_plan_mediator

    result = build_confirm_ai_plan_mediator(db).send(ConfirmAiPlanCommand(
        user_id=command_draft["user_id"], draft_id=command_draft["draft_id"],
    ))
    assert result.goal.title == "Command goal"
    assert result.task_with_schedule_list[0].task.title == "Command task"
    assert not db.in_transaction()
    assert state(db.get_bind(), command_draft) == ([1, 1, 1, 1], True)


def test_confirmation_handler_does_not_commit_independently(db, command_draft):
    from app.ai_planner.dependencies import build_ai_draft_service
    from app.workflows.task_workflow.commands import ConfirmAiPlanCommand
    from app.workflows.task_workflow.dependencies import build_task_workflow_service
    from app.workflows.task_workflow.handlers import ConfirmAiPlanCommandHandler

    with Session(db.get_bind()) as session:
        handler = ConfirmAiPlanCommandHandler(build_ai_draft_service(session), build_task_workflow_service(session))
        result = handler.handle(ConfirmAiPlanCommand(
            user_id=command_draft["user_id"], draft_id=command_draft["draft_id"],
        ))
        assert result.goal.title == "Command goal"
        assert session.get(AIPlanDraft, command_draft["draft_id"]).consumed_at is not None
        assert state(db.get_bind(), command_draft) == ([0, 0, 0, 0], False)
        session.rollback()
    assert state(db.get_bind(), command_draft) == ([0, 0, 0, 0], False)


@pytest.mark.parametrize("field,value", [
    ("draft_id", None), ("draft_id", "not-a-uuid"), ("draft_id", str(uuid4())),
    ("draft_id", 1), ("user_id", None), ("user_id", "not-a-uuid"),
])
def test_confirmation_command_rejects_invalid_ids_before_transaction(db, command_draft, field, value, monkeypatch):
    from app.workflows.task_workflow.commands import ConfirmAiPlanCommand
    from app.workflows.task_workflow.dependencies import build_confirm_ai_plan_mediator

    command = ConfirmAiPlanCommand(**{**{key: command_draft[key] for key in ["user_id", "draft_id"]}, field: value})
    mediator = build_confirm_ai_plan_mediator(db)

    def unexpected_commit():
        pytest.fail("Invalid command must not open a write transaction")

    monkeypatch.setattr(db, "commit", unexpected_commit)
    with pytest.raises(RequestValidationError) as error:
        mediator.send(command)
    assert error.value.details["issues"][0]["field"] == field
    assert not db.in_transaction()
    assert state(db.get_bind(), command_draft) == ([0, 0, 0, 0], False)


def test_confirmation_command_cannot_use_another_users_draft(db, command_draft):
    from app.workflows.task_workflow.commands import ConfirmAiPlanCommand
    from app.workflows.task_workflow.dependencies import build_confirm_ai_plan_mediator

    other = User(email=f"other-confirm-{uuid4()}@example.com", password_hash="unused")
    db.add(other)
    db.commit()
    other_id = other.id
    db.rollback()
    with pytest.raises(NotFoundError):
        build_confirm_ai_plan_mediator(db).send(ConfirmAiPlanCommand(
            user_id=other_id, draft_id=command_draft["draft_id"],
        ))
    assert not db.in_transaction()
    assert state(db.get_bind(), command_draft) == ([0, 0, 0, 0], False)


def test_confirmation_command_rolls_back_commit_failure_and_can_retry(db, command_draft, monkeypatch, caplog):
    from app.workflows.task_workflow.commands import ConfirmAiPlanCommand
    from app.workflows.task_workflow.dependencies import build_confirm_ai_plan_mediator

    mediator = build_confirm_ai_plan_mediator(db)
    command = ConfirmAiPlanCommand(user_id=command_draft["user_id"], draft_id=command_draft["draft_id"])

    def fail_commit():
        assert db.get(AIPlanDraft, command_draft["draft_id"]).consumed_at is not None
        assert db.scalar(select(func.count()).select_from(Task).where(Task.user_id == command_draft["user_id"])) == 1
        raise RuntimeError("injected confirmation commit failure")

    with monkeypatch.context() as patch, caplog.at_level(logging.INFO, logger="app.cqrs"):
        patch.setattr(db, "commit", fail_commit)
        with pytest.raises(RuntimeError, match="injected confirmation commit failure"):
            mediator.send(command)
    assert not db.in_transaction()
    assert db.is_active
    assert state(db.get_bind(), command_draft) == ([0, 0, 0, 0], False)
    assert any(getattr(record, "request_type", None) == "ConfirmAiPlanCommand"
               and record.outcome == "failure" for record in caplog.records)
    assert mediator.send(command).goal.title == "Command goal"
    assert state(db.get_bind(), command_draft) == ([1, 1, 1, 1], True)
    with pytest.raises(AppError) as error:
        mediator.send(command)
    assert error.value.code == "AI_DRAFT_CONSUMED"
    assert state(db.get_bind(), command_draft) == ([1, 1, 1, 1], True)
