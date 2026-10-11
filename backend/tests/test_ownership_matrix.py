"""Ownership matrix: actor x resource/action, including indirect references.

Private resources use 404 for foreign IDs; anonymous access uses 401.
System scoring schemes (null owner) may be used but not edited by users.
Only the internal scheduler may generate instances across all users.
PointLedger.source_id is descriptive metadata, not an authorization grant.
Soft-delete combinations are covered by test_ownership_soft_delete_matrix.py.
"""

from datetime import date
from types import SimpleNamespace

import pytest

from app.errors.exception import NotFoundError
from app.scoring_schemes.models import ScoringScheme
from app.task_instances.commands import CompleteTaskInstanceCommand, GenerateDailyTaskInstancesCommand
from app.task_instances.dependencies import (
    build_complete_task_instance_mediator,
    build_generate_task_instances_mediator,
    build_task_instance_service,
)
from app.task_instances.models import TaskInstance
from app.tasks.models import Task
from app.workflows.redemption_workflow.commands import RedeemRewardCommand
from app.workflows.redemption_workflow.dependencies import build_redeem_reward_mediator
from app.workflows.task_workflow.commands import CreateTaskWithScheduleCommand
from app.workflows.task_workflow.dependencies import build_create_task_with_schedule_mediator
from app.workflows.task_workflow.dtos import CreateTaskWithScheduleDTO
from app.tasks.dtos import CreateTaskDTO
from ownership_support import EDIT_CASES, LIST_CASES, RESOURCE_MODELS, ids_for, snapshot


READ_RESOURCES = ["goals", "tasks", "task_schedules", "scoring_schemes", "rewards", "redemptions", "users"]


@pytest.mark.parametrize("actor,want", [("owner", 200), ("other", 404), ("anonymous", 401)])
@pytest.mark.parametrize("resource", READ_RESOURCES)
def test_resource_read_matrix(client, db, ownership_case, actor, want, resource):
    case = ownership_case
    before = snapshot(db, case)
    response = client.get(f"/{resource}/{ids_for(case)[resource]}", headers=case[actor]["headers"])
    assert response.status_code == want, response.text
    if actor == "owner":
        assert str(response.json()["id"]) == str(ids_for(case)[resource])
        assert "password_hash" not in response.json()
    assert snapshot(db, case) == before


@pytest.mark.parametrize("actor", ["owner", "other", "anonymous"])
@pytest.mark.parametrize("action", ["update", "delete"])
@pytest.mark.parametrize("resource,payload", EDIT_CASES)
def test_resource_write_matrix(client, db, ownership_case, actor, action, resource, payload):
    case = ownership_case
    before = snapshot(db, case)
    path = f"/{resource}/{ids_for(case)[resource]}"
    if action == "delete":
        path += "/delete"
    response = client.post(path, headers=case[actor]["headers"], json=payload if action == "update" else None)
    want = (204 if action == "delete" else 200) if actor == "owner" else (404 if actor == "other" else 401)
    assert response.status_code == want, response.text
    if actor != "owner":
        assert snapshot(db, case) == before
    else:
        row = db.get(RESOURCE_MODELS[resource], ids_for(case)[resource])
        db.refresh(row)
        if action == "delete":
            assert row.deleted_at is not None
        elif resource == "task_schedules":
            assert row.end_date == date(2045, 6, 1)
        else:
            assert row.title == "Changed"


@pytest.mark.parametrize("actor", ["owner", "other", "anonymous"])
@pytest.mark.parametrize("resource,path", LIST_CASES)
def test_list_only_returns_authenticated_users_rows(client, db, ownership_case, actor, resource, path):
    case = ownership_case
    before = snapshot(db, case)
    response = client.get(path, headers=case[actor]["headers"])
    assert response.status_code == (401 if actor == "anonymous" else 200), response.text
    if actor != "anonymous":
        rows = response.json()
        assert case[actor]["rows"][resource].id in {row["id"] for row in rows}
        assert all(row["user_id"] == str(case[actor]["user"].id) for row in rows)
    assert snapshot(db, case) == before


@pytest.mark.parametrize("actor", ["owner", "other", "anonymous"])
@pytest.mark.parametrize("action", ["list_tasks", "create_task", "workflow_task", "list_schedules", "create_schedule", "create_instance", "complete", "redemption", "redeem"])
def test_nested_and_workflow_ownership_matrix(client, db, ownership_case, actor, action):
    case = ownership_case
    ids = ids_for(case)
    scheme_id = case[actor if actor != "anonymous" else "owner"]["rows"]["scoring_schemes"].id
    task_payload = {"title": "New task", "scoring_scheme_id": scheme_id}
    requests = {
        "list_tasks": ("GET", f"/goals/{ids['goals']}/tasks", None, 200),
        "create_task": ("POST", f"/goals/{ids['goals']}/tasks", task_payload, 201),
        "workflow_task": ("POST", f"/workflows/goals/{ids['goals']}/tasks", {"task": task_payload}, 201),
        "list_schedules": ("GET", f"/tasks/{ids['tasks']}/task_schedules", None, 200),
        "create_schedule": ("POST", f"/tasks/{ids['tasks']}/task_schedules", {"schedule_type": "daily", "schedule_value_json": {}}, 201),
        "create_instance": ("POST", f"/tasks/{ids['tasks']}/task_schedules/{ids['task_schedules']}/task_instances", {"date_instance": "2045-05-11"}, 201),
        "complete": ("POST", f"/task_instances/{ids['task_instances']}/complete", {"completion_level": "normal"}, 200),
        "redemption": ("POST", "/redemptions", {"reward_id": ids["rewards"]}, 201),
        "redeem": ("POST", f"/workflows/rewards/{ids['rewards']}/redeem", None, 200),
    }
    method, path, payload, success = requests[action]
    before = snapshot(db, case)
    response = client.request(method, path, headers=case[actor]["headers"], json=payload)
    assert response.status_code == (success if actor == "owner" else 404 if actor == "other" else 401), response.text
    if actor != "owner":
        assert snapshot(db, case) == before
    elif action.startswith("list_"):
        assert response.json()
        assert all(row["user_id"] == str(case["owner"]["user"].id) for row in response.json())
    else:
        result = response.json()
        if action == "workflow_task":
            result = result["task"]
        elif action == "complete":
            result = result["task_instance"]
        if action != "redeem":
            assert result["user_id"] == str(case["owner"]["user"].id)


@pytest.mark.parametrize("action", ["create", "update", "workflow"])
def test_task_cannot_reference_another_users_scoring_scheme(client, db, ownership_case, action):
    case = ownership_case
    ids = ids_for(case)
    payload = {"title": "Forbidden reference", "scoring_scheme_id": ids_for(case, "other")["scoring_schemes"]}
    path = f"/goals/{ids['goals']}/tasks"
    if action == "update":
        path = f"/tasks/{ids['tasks']}"
    elif action == "workflow":
        path = f"/workflows/goals/{ids['goals']}/tasks"
        payload = {"task": payload, "schedule": {"schedule_type": "once", "schedule_value_json": {}, "start_date": "2045-05-11"}}
    before = snapshot(db, case)
    response = client.post(path, headers=case["owner"]["headers"], json=payload)
    assert response.status_code == 404, response.text
    assert snapshot(db, case) == before


@pytest.mark.parametrize("action", ["create", "update", "workflow", "default", "default_zero"])
def test_system_scoring_scheme_remains_usable(client, db, ownership_case, monkeypatch, action):
    case = ownership_case
    scheme = ScoringScheme(title="System scheme", levels_json={"normal": 1}, user_id=None)
    db.add(scheme)
    db.commit()
    ids = ids_for(case)
    payload = {"title": "Uses system scheme", "scoring_scheme_id": scheme.id}
    path = f"/goals/{ids['goals']}/tasks"
    if action == "update":
        path = f"/tasks/{ids['tasks']}"
    elif action == "workflow":
        path = f"/workflows/goals/{ids['goals']}/tasks"
        payload = {"task": payload}
    elif action in ("default", "default_zero"):
        monkeypatch.setattr("app.shared.function.SCORING_SCHME_ID", SimpleNamespace(DEFAULT=scheme.id))
        payload["scoring_scheme_id"] = None if action == "default" else 0
    response = client.post(path, headers=case["owner"]["headers"], json=payload)
    assert response.status_code == (200 if action == "update" else 201), response.text
    result = response.json()["task"] if action == "workflow" else response.json()
    assert result["scoring_scheme_id"] == scheme.id


@pytest.mark.parametrize("scheme_id", [None, 0])
@pytest.mark.parametrize("entrypoint", ["task", "workflow"])
def test_default_id_cannot_bypass_private_scheme_ownership(
    client, db, ownership_case, monkeypatch, scheme_id, entrypoint,
):
    case = ownership_case
    monkeypatch.setattr("app.shared.function.SCORING_SCHME_ID", SimpleNamespace(DEFAULT=ids_for(case, "other")["scoring_schemes"]))
    before = snapshot(db, case)
    path = f"/goals/{ids_for(case)['goals']}/tasks"
    payload = {"title": "Default bypass", "scoring_scheme_id": scheme_id}
    if entrypoint == "workflow":
        path = f"/workflows/goals/{ids_for(case)['goals']}/tasks"
        payload = {"task": payload}
    response = client.post(path, headers=case["owner"]["headers"], json=payload)
    assert response.status_code == 404, response.text
    assert snapshot(db, case) == before


@pytest.mark.parametrize("foreign_part", ["task", "schedule", "different_owned_task"])
def test_instance_creation_rejects_mismatched_parents(client, db, ownership_case, foreign_part):
    case = ownership_case
    ids = ids_for(case)
    task_id, schedule_id = ids["tasks"], ids["task_schedules"]
    if foreign_part == "task":
        task_id = ids_for(case, "other")["tasks"]
    elif foreign_part == "schedule":
        schedule_id = ids_for(case, "other")["task_schedules"]
    else:
        task = Task(user=case["owner"]["user"], goal=case["owner"]["rows"]["goals"], title="Another owned task")
        db.add(task)
        db.commit()
        task_id = task.id
    before = snapshot(db, case)
    response = client.post(f"/tasks/{task_id}/task_schedules/{schedule_id}/task_instances", headers=case["owner"]["headers"], json={"date_instance": "2045-05-11"})
    assert response.status_code == 404, response.text
    assert snapshot(db, case) == before


@pytest.mark.parametrize("actor", ["owner", "other", "anonymous"])
def test_manual_generation_is_authenticated_and_user_scoped(client, db, ownership_case, actor):
    case = ownership_case
    before = snapshot(db, case)
    target = date(2045, 5, 12)
    response = client.post("/tasks_instances/generate", headers=case[actor]["headers"], json={"date_instance": target.isoformat()})
    assert response.status_code == (401 if actor == "anonymous" else 201), response.text
    if actor == "anonymous":
        assert snapshot(db, case) == before
    else:
        assert len(response.json()) == 1
        assert response.json()[0]["user_id"] == str(case[actor]["user"].id)
        other = "other" if actor == "owner" else "owner"
        assert db.query(TaskInstance).filter(TaskInstance.user_id == case[other]["user"].id, TaskInstance.date_instance == target).count() == 0


def test_task_workflow_does_not_generate_other_users_instances(client, db, ownership_case):
    case = ownership_case
    response = client.post(f"/workflows/goals/{ids_for(case)['goals']}/tasks", headers=case["owner"]["headers"], json={
        "task": {"title": "Scoped workflow", "scoring_scheme_id": ids_for(case)["scoring_schemes"]},
        "schedule": {"schedule_type": "daily", "schedule_value_json": {}, "start_date": date.today().isoformat()},
    })
    assert response.status_code == 201, response.text
    assert db.query(TaskInstance).filter(TaskInstance.user_id == case["other"]["user"].id, TaskInstance.date_instance == date.today()).count() == 0
    assert db.query(TaskInstance).filter(TaskInstance.task_id == response.json()["task"]["id"], TaskInstance.date_instance == date.today()).count() == 1


def test_scheduler_still_generates_for_all_users(db, ownership_case):
    result = build_generate_task_instances_mediator(db).send(GenerateDailyTaskInstancesCommand(target_date=date(2045, 5, 13)))
    returned = {row.task_id for row in result.task_instances}
    assert {ids_for(ownership_case, actor)["tasks"] for actor in ("owner", "other")} <= returned


@pytest.mark.parametrize("action", ["complete", "redeem", "create_task", "private_scheme", "instance"])
def test_non_http_entrypoints_enforce_ownership(db, ownership_case, action):
    case = ownership_case
    ids = ids_for(case)
    other_id = case["other"]["user"].id
    before = snapshot(db, case)
    with pytest.raises(NotFoundError):
        if action == "complete":
            build_complete_task_instance_mediator(db).send(CompleteTaskInstanceCommand(task_instance_id=ids["task_instances"], user_id=other_id, completion_level="normal"))
        elif action == "redeem":
            build_redeem_reward_mediator(db).send(RedeemRewardCommand(reward_id=ids["rewards"], user_id=other_id))
        elif action in ("create_task", "private_scheme"):
            goal_id = ids["goals"] if action == "create_task" else ids_for(case, "other")["goals"]
            build_create_task_with_schedule_mediator(db).send(CreateTaskWithScheduleCommand(goal_id=goal_id, user_id=other_id,
                payload=CreateTaskWithScheduleDTO(task=CreateTaskDTO(title="Forbidden", scoring_scheme_id=ids["scoring_schemes"]))))
        else:
            build_task_instance_service(db).create_task_instance_for_date(task_id=ids["tasks"], task_schedule_id=ids["task_schedules"], user_id=other_id, date_instance=date(2045, 5, 14))
    assert snapshot(db, case) == before


@pytest.mark.parametrize("path", ["/point_ledgers/balance", "/point_ledgers/reconciliation", "/users/me"])
def test_user_summary_ignores_supplied_other_user_id(client, ownership_case, path):
    case = ownership_case
    response = client.get(path, headers=case["other"]["headers"], params={"user_id": str(case["owner"]["user"].id)})
    assert response.status_code == 200, response.text
    if path == "/users/me":
        assert response.json()["id"] == str(case["other"]["user"].id)
    elif path.endswith("reconciliation"):
        assert response.json()["cached_balance"] == 200
        assert response.json()["ledger_balance"] == 200
    else:
        assert response.json()["balance"] == 200


@pytest.mark.parametrize("actor", ["owner", "other", "anonymous"])
def test_point_posting_cannot_select_another_users_account(client, db, ownership_case, actor):
    case = ownership_case
    before = snapshot(db, case)
    response = client.post("/point_ledgers", headers=case[actor]["headers"], json={
        "delta": 7, "entry_type": "earn", "user_id": str(case["owner"]["user"].id),
    })
    assert response.status_code == (401 if actor == "anonymous" else 201), response.text
    if actor == "anonymous":
        assert snapshot(db, case) == before
    else:
        assert response.json()["user_id"] == str(case[actor]["user"].id)
        db.expire_all()
        assert case[actor]["user"].current_value == (107 if actor == "owner" else 207)
        other = "other" if actor == "owner" else "owner"
        assert case[other]["user"].current_value == (200 if other == "other" else 100)


@pytest.mark.parametrize("actor", ["owner", "other", "anonymous"])
@pytest.mark.parametrize("resource,payload", [
    ("goals", {"title": "New goal", "start_date": "2045-05-10"}),
    ("scoring_schemes", {"title": "New scheme", "levels_json": {"normal": 1}}),
    ("rewards", {"title": "New reward", "cost_points": 10}),
])
def test_root_creation_uses_authenticated_user_not_payload(client, db, ownership_case, actor, resource, payload):
    case = ownership_case
    before = snapshot(db, case)
    response = client.post(f"/{resource}", headers=case[actor]["headers"], json={
        **payload, "user_id": str(case["owner"]["user"].id),
    })
    assert response.status_code == (401 if actor == "anonymous" else 201), response.text
    if actor == "anonymous":
        assert snapshot(db, case) == before
    else:
        row = db.get(RESOURCE_MODELS[resource], response.json()["id"])
        assert row.user_id == case[actor]["user"].id


@pytest.mark.parametrize("action", ["read", "update", "delete"])
def test_system_scheme_is_not_a_user_editable_resource(client, db, ownership_case, action):
    case = ownership_case
    scheme = ScoringScheme(title="Read-only system scheme", levels_json={"normal": 1}, user_id=None)
    db.add(scheme)
    db.commit()
    path = f"/scoring_schemes/{scheme.id}"
    if action == "delete":
        path += "/delete"
    response = client.request("GET" if action == "read" else "POST", path,
                              headers=case["owner"]["headers"], json={"title": "Changed"} if action == "update" else None)
    assert response.status_code == 404, response.text
    db.refresh(scheme)
    assert scheme.title == "Read-only system scheme"
    assert scheme.deleted_at is None


@pytest.mark.parametrize("actor", ["owner", "other", "anonymous"])
def test_ai_confirmation_only_creates_for_authenticated_user(client, db, ownership_case, monkeypatch, actor):
    case = ownership_case
    scheme = ScoringScheme(title="AI system default", levels_json={"normal": 1}, user_id=None)
    db.add(scheme)
    db.commit()
    monkeypatch.setattr("app.shared.function.SCORING_SCHME_ID", SimpleNamespace(DEFAULT=scheme.id))
    before = snapshot(db, case)
    response = client.post("/workflows/ai/confirm", headers=case[actor]["headers"], json={
        "user_id": str(case["owner"]["user"].id),
        "plan": {"goal_title": "AI ownership", "tasks": [{
            "title": "AI task", "schedule_type": "daily", "schedule_value_json": {},
            "user_id": str(case["owner"]["user"].id),
        }]},
    })
    assert response.status_code == (401 if actor == "anonymous" else 201), response.text
    if actor == "anonymous":
        assert snapshot(db, case) == before
    else:
        result = response.json()
        user_id = str(case[actor]["user"].id)
        assert result["goal"]["user_id"] == user_id
        assert result["task_with_schedule_list"][0]["task"]["user_id"] == user_id
        other = "other" if actor == "owner" else "owner"
        assert db.query(TaskInstance).filter(TaskInstance.user_id == case[other]["user"].id, TaskInstance.date_instance == date.today()).count() == 0


def test_ai_confirmation_rolls_back_goal_when_default_scheme_is_foreign(
    client, db, ownership_case, monkeypatch,
):
    case = ownership_case
    monkeypatch.setattr("app.shared.function.SCORING_SCHME_ID", SimpleNamespace(
        DEFAULT=ids_for(case, "other")["scoring_schemes"],
    ))
    before = snapshot(db, case)
    response = client.post("/workflows/ai/confirm", headers=case["owner"]["headers"], json={
        "plan": {"goal_title": "Must roll back", "tasks": [{
            "title": "Forbidden default", "schedule_type": "daily", "schedule_value_json": {},
        }]},
    })
    assert response.status_code == 404, response.text
    assert snapshot(db, case) == before


def test_user_scoped_generation_keeps_inactive_tasks_excluded(client, db, ownership_case):
    case = ownership_case
    case["owner"]["rows"]["tasks"].is_active = False
    db.commit()
    response = client.post("/tasks_instances/generate", headers=case["owner"]["headers"], json={"date_instance": "2045-05-15"})
    assert response.status_code == 201, response.text
    assert response.json() == []
    assert db.query(TaskInstance).filter(TaskInstance.user_id.in_([case["owner"]["user"].id, case["other"]["user"].id]), TaskInstance.date_instance == date(2045, 5, 15)).count() == 0


def test_repeated_user_scoped_generation_returns_same_owned_instance(client, db, ownership_case):
    case = ownership_case
    first = client.post("/tasks_instances/generate", headers=case["owner"]["headers"],
                        json={"date_instance": "2045-05-16"})
    second = client.post("/tasks_instances/generate", headers=case["owner"]["headers"],
                         json={"date_instance": "2045-05-16"})
    assert first.status_code == second.status_code == 201
    assert len(first.json()) == len(second.json()) == 1
    assert first.json()[0]["id"] == second.json()[0]["id"]
    assert first.json()[0]["user_id"] == str(case["owner"]["user"].id)
    assert db.query(TaskInstance).filter(
        TaskInstance.task_id == ids_for(case)["tasks"],
        TaskInstance.date_instance == date(2045, 5, 16),
    ).count() == 1
