from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.auth.security import create_access_token
from app.point_ledgers.models import PointLedger
from app.task_instances.models import TaskInstance
from app.task_instances.commands import CompleteTaskInstanceCommand
from app.task_instances.dependencies import build_complete_task_instance_mediator
from app.task_instances.repository import TaskInstanceRepository
from app.task_schedules.models import TaskSchedule
from app.task_schedules.service import TaskScheduleService
from app.tasks.models import Task
from app.users.models import User


TARGET = date(2045, 5, 10)


@pytest.fixture
def todo_actor(db):
    user = User(email=f"todo-{uuid4()}@example.com", password_hash="unused")
    db.add(user)
    db.commit()
    actor = {"id": user.id, "headers": {"Authorization": f"Bearer {create_access_token(sub=str(user.id))}"}}
    db.rollback()
    return actor


def create_todo(client, actor, schedule_type="once", **task_fields):
    schedule_value = {"days": [TARGET.weekday()]} if schedule_type == "weekly" else {"day": TARGET.day} if schedule_type == "monthly" else {}
    return client.post("/workflows/tasks", headers=actor["headers"], json={
        "task": {"title": "Buy milk", **task_fields},
        "schedule": {"schedule_type": schedule_type, "schedule_value_json": schedule_value, "start_date": TARGET.isoformat()},
    })


@pytest.mark.parametrize("schedule_type", ["once", "daily", "weekly", "monthly"])
def test_standalone_todo_creation_listing_and_generation(client, todo_actor, schedule_type):
    response = create_todo(client, todo_actor, schedule_type)
    assert response.status_code == 201, response.text
    result = response.json()
    task, schedule = result["task"], result["schedule"]
    assert task["goal_id"] is None
    assert task["scoring_scheme_id"] is None
    assert task["scoring_scheme_json"] is None
    assert task["user_id"] == str(todo_actor["id"])
    assert client.get(f"/tasks/{task['id']}", headers=todo_actor["headers"]).status_code == 200
    assert task["id"] in {row["id"] for row in client.get("/tasks", headers=todo_actor["headers"]).json()}
    assert schedule["id"] in {row["id"] for row in client.get("/task_schedules", headers=todo_actor["headers"]).json()}
    if schedule_type != "once":
        generated = client.post("/tasks_instances/generate", headers=todo_actor["headers"], json={"date_instance": TARGET.isoformat()})
        assert generated.status_code == 201, generated.text
        instance = next(row for row in generated.json() if row["task_id"] == task["id"])
    else:
        instance = result["task_instance"]
    assert instance["scoring_snapshot_json"] is None
    assert instance["score_awarded"] == 0


def test_create_standalone_task_without_schedule_and_update(client, todo_actor):
    response = client.post("/tasks", headers=todo_actor["headers"], json={"title": "Todo template"})
    assert response.status_code == 201, response.text
    task = response.json()
    assert task["goal_id"] is None
    response = client.post(f"/tasks/{task['id']}", headers=todo_actor["headers"], json={"title": "Updated"})
    assert response.status_code == 200
    assert response.json()["title"] == "Updated"


@pytest.mark.parametrize("payload", [{}, {"completion_level": None}])
def test_standalone_completion_is_unscored_and_retry_safe(client, db, todo_actor, payload):
    created = create_todo(client, todo_actor)
    assert created.status_code == 201, created.text
    instance_id = created.json()["task_instance"]["id"]
    path = f"/task_instances/{instance_id}/complete"
    for _ in range(2):
        response = client.post(path, headers=todo_actor["headers"], json=payload)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["task_instance"]["status"] == "done"
        assert result["task_instance"]["completion_level"] is None
        assert result["task_instance"]["score_awarded"] == 0
        assert result["point_ledger"] is None
    with Session(db.get_bind()) as reader:
        assert reader.get(User, todo_actor["id"]).current_value == 0
        assert reader.query(PointLedger).filter_by(user_id=todo_actor["id"]).count() == 0


@pytest.mark.parametrize("task_fields", [{"scoring_scheme_id": 1}, {"scoring_scheme_json": {"done": 999}}])
def test_standalone_creation_rejects_score_configuration(client, db, todo_actor, task_fields):
    response = create_todo(client, todo_actor, **task_fields)
    assert response.status_code == 422, response.text
    assert db.query(Task).filter_by(user_id=todo_actor["id"]).count() == 0


@pytest.mark.parametrize("changes", [{"scoring_scheme_id": 1}, {"scoring_scheme_json": {"done": 999}}])
def test_standalone_update_cannot_enable_scoring(client, db, todo_actor, changes):
    created = create_todo(client, todo_actor)
    assert created.status_code == 201, created.text
    task_id = created.json()["task"]["id"]
    response = client.post(f"/tasks/{task_id}", headers=todo_actor["headers"], json=changes)
    assert response.status_code == 422
    db.expire_all()
    task = db.get(Task, task_id)
    assert task.scoring_scheme_id is None and task.scoring_scheme_json is None


def test_standalone_completion_rejects_injected_level_without_changes(client, db, todo_actor):
    created = create_todo(client, todo_actor)
    assert created.status_code == 201, created.text
    instance_id = created.json()["task_instance"]["id"]
    response = client.post(f"/task_instances/{instance_id}/complete", headers=todo_actor["headers"], json={"completion_level": "done"})
    assert response.status_code == 422
    db.expire_all()
    assert db.get(TaskInstance, instance_id).status == "todo"


def test_standalone_workflow_rollback(client, db, todo_actor, monkeypatch):
    def fail(self, task_id, user_id, payload):
        raise RuntimeError("schedule failure")
    monkeypatch.setattr(TaskScheduleService, "create_task_schedule", fail)
    with pytest.raises(RuntimeError, match="schedule failure"):
        create_todo(client, todo_actor)
    assert db.query(Task).filter_by(user_id=todo_actor["id"]).count() == 0
    assert db.query(TaskSchedule).filter_by(user_id=todo_actor["id"]).count() == 0


def test_standalone_resources_remain_private_and_deleted_tasks_stop_generation(client, db, todo_actor, ownership_case):
    created = create_todo(client, todo_actor, "daily")
    assert created.status_code == 201, created.text
    task_id, schedule_id = created.json()["task"]["id"], created.json()["schedule"]["id"]
    foreign = ownership_case["other"]["headers"]
    assert client.get(f"/tasks/{task_id}", headers=foreign).status_code == 404
    assert client.post(f"/tasks/{task_id}", headers=foreign, json={"title": "Hijack"}).status_code == 404
    assert client.get(f"/task_schedules/{schedule_id}", headers=foreign).status_code == 404
    assert client.post(f"/tasks/{task_id}/delete", headers=todo_actor["headers"]).status_code == 204
    response = client.post("/tasks_instances/generate", headers=todo_actor["headers"], json={"date_instance": TARGET.isoformat()})
    assert response.status_code == 201
    assert not any(row["task_id"] == task_id for row in response.json())


def test_generic_workflow_accepts_owned_goal_and_rejects_foreign_goal(client, ownership_case):
    case = ownership_case
    owner = case["owner"]
    payload = {"goal_id": owner["rows"]["goals"].id, "task": {"title": "Goal task", "scoring_scheme_id": owner["rows"]["scoring_schemes"].id}}
    response = client.post("/workflows/tasks", headers=owner["headers"], json=payload)
    assert response.status_code == 201, response.text
    assert response.json()["task"]["goal_id"] == payload["goal_id"]
    assert client.post("/workflows/tasks", headers=case["other"]["headers"], json=payload).status_code == 404
    assert client.post("/workflows/tasks", json=payload).status_code == 401


@pytest.mark.parametrize("delta", [100, -100, 0])
def test_public_point_writes_are_forbidden_even_with_forged_source(client, db, todo_actor, delta):
    response = client.post("/point_ledgers", headers=todo_actor["headers"], json={"delta": delta, "entry_type": "earn", "source_type": "task_instance", "source_id": 1})
    assert response.status_code == 403, response.text
    with Session(db.get_bind()) as reader:
        assert reader.get(User, todo_actor["id"]).current_value == 0
        assert reader.query(PointLedger).filter_by(user_id=todo_actor["id"]).count() == 0


def test_goal_completion_can_infer_single_snapshot_level(client, db, task_instance, auth_headers):
    instance = db.get(TaskInstance, task_instance["id"])
    instance.scoring_snapshot_json = {"done": 7}
    db.commit()
    response = client.post(f"/task_instances/{instance.id}/complete", headers=auth_headers, json={})
    assert response.status_code == 200, response.text
    assert response.json()["task_instance"]["score_awarded"] == 7


def test_multi_level_goal_still_requires_a_choice(client, task_instance, auth_headers):
    response = client.post(f"/task_instances/{task_instance['id']}/complete", headers=auth_headers, json={})
    assert response.status_code == 422


@pytest.mark.parametrize("snapshot", [None, {}])
def test_missing_goal_score_snapshot_is_not_silently_completed(client, db, task_instance, auth_headers, snapshot):
    instance_id = task_instance["id"]
    instance = db.get(TaskInstance, instance_id)
    instance.scoring_snapshot_json = snapshot
    db.commit()
    response = client.post(f"/task_instances/{instance_id}/complete", headers=auth_headers, json={})
    assert response.status_code == 422
    db.expire_all()
    assert db.get(TaskInstance, instance_id).status == "todo"


@pytest.mark.parametrize("title", ["   ", "x" * 256])
@pytest.mark.parametrize("path", ["/tasks", "/workflows/tasks"])
def test_new_task_routes_validate_titles_before_writing(client, db, todo_actor, title, path):
    payload = {"title": title} if path == "/tasks" else {"task": {"title": title}}
    response = client.post(path, headers=todo_actor["headers"], json=payload)
    assert response.status_code == 422
    assert db.query(Task).filter_by(user_id=todo_actor["id"]).count() == 0


def test_standalone_completion_foreign_and_anonymous_access(client, db, todo_actor, ownership_case):
    created = create_todo(client, todo_actor)
    assert created.status_code == 201, created.text
    instance_id = created.json()["task_instance"]["id"]
    path = f"/task_instances/{instance_id}/complete"
    assert client.post(path, headers=ownership_case["other"]["headers"], json={}).status_code == 404
    assert client.post(path, json={}).status_code == 401
    db.expire_all()
    assert db.get(TaskInstance, instance_id).status == "todo"


def test_standalone_completion_failure_rolls_back_status(client, db, todo_actor, monkeypatch):
    created = create_todo(client, todo_actor)
    assert created.status_code == 201, created.text
    instance_id = created.json()["task_instance"]["id"]
    original = TaskInstanceRepository.update

    def fail_after_update(self, task_instance):
        original(self, task_instance)
        raise RuntimeError("completion failure")

    monkeypatch.setattr(TaskInstanceRepository, "update", fail_after_update)
    with pytest.raises(RuntimeError, match="completion failure"):
        client.post(f"/task_instances/{instance_id}/complete", headers=todo_actor["headers"], json={})
    with Session(db.get_bind()) as reader:
        assert reader.get(TaskInstance, instance_id).status == "todo"
        assert reader.query(PointLedger).filter_by(user_id=todo_actor["id"]).count() == 0


def test_concurrent_standalone_completion_remains_unscored(client, db, todo_actor):
    created = create_todo(client, todo_actor)
    assert created.status_code == 201, created.text
    instance_id = created.json()["task_instance"]["id"]
    ready = Barrier(2)
    bind = db.get_bind()

    def complete():
        with Session(bind) as session:
            ready.wait(timeout=10)
            result = build_complete_task_instance_mediator(session).send(CompleteTaskInstanceCommand(
                task_instance_id=instance_id, user_id=todo_actor["id"],
            ))
            return result.task_instance.status, result.task_instance.score_awarded, result.point_ledger

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(complete) for _ in range(2)]
        assert [future.result(timeout=20) for future in futures] == [("done", 0, None)] * 2
    with Session(bind) as reader:
        assert reader.get(User, todo_actor["id"]).current_value == 0
        assert reader.query(PointLedger).filter_by(user_id=todo_actor["id"]).count() == 0
