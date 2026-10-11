"""Cross-user and deleted-state combinations, including retained history."""

from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from app.errors.exception import NotFoundError
from app.goals.repository import GoalRepository
from app.point_ledgers.repository import PointLedgerRepository
from app.redemptions.repository import RedemptionRepository
from app.rewards.models import Reward
from app.rewards.repository import RewardRepository
from app.scoring_schemes.models import ScoringScheme
from app.scoring_schemes.repository import ScoringSchemeRepository
from app.task_instances.commands import CompleteTaskInstanceCommand, GenerateDailyTaskInstancesCommand
from app.task_instances.dependencies import (
    build_complete_task_instance_mediator, build_generate_task_instances_mediator,
)
from app.task_instances.models import TaskInstance
from app.task_instances.repository import TaskInstanceRepository
from app.task_schedules.repository import TaskScheduleRepository
from app.tasks.dtos import CreateTaskDTO
from app.tasks.repository import TaskRepository
from app.workflows.redemption_workflow.commands import RedeemRewardCommand
from app.workflows.redemption_workflow.dependencies import build_redeem_reward_mediator
from app.workflows.task_workflow.commands import CreateTaskWithScheduleCommand
from app.workflows.task_workflow.dependencies import build_create_task_with_schedule_mediator
from app.workflows.task_workflow.dtos import CreateTaskWithScheduleDTO
from ownership_support import EDIT_CASES, LIST_CASES, RESOURCE_MODELS, ids_for, snapshot


ACTORS = ["owner", "other", "anonymous"]
REPOSITORIES = {
    "goals": GoalRepository, "tasks": TaskRepository,
    "task_schedules": TaskScheduleRepository, "task_instances": TaskInstanceRepository,
    "scoring_schemes": ScoringSchemeRepository, "rewards": RewardRepository,
    "redemptions": RedemptionRepository, "point_ledgers": PointLedgerRepository,
}


def mark_deleted(db, case, resource):
    row = case["owner"]["user"] if resource == "users" else case["owner"]["rows"][resource]
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return row


DELETED_ACCESS_CASES = [
    (resource, action, payload)
    for resource, payload in EDIT_CASES for action in ("read", "update", "delete")
] + [("redemptions", "read", None)]


@pytest.mark.parametrize("actor", ACTORS)
@pytest.mark.parametrize("resource,action,payload", DELETED_ACCESS_CASES)
def test_deleted_resource_cannot_be_read_changed_or_deleted_again(
    client, db, ownership_case, actor, resource, action, payload,
):
    case = ownership_case
    row = mark_deleted(db, case, resource)
    before = snapshot(db, case)
    path = f"/{resource}/{row.id}"
    if action == "delete":
        path += "/delete"
    response = client.request(
        "GET" if action == "read" else "POST", path,
        headers=case[actor]["headers"], json=payload if action == "update" else None,
    )
    assert response.status_code == (401 if actor == "anonymous" else 404), response.text
    assert snapshot(db, case) == before
    assert db.get(RESOURCE_MODELS[resource], row.id).deleted_at is not None


@pytest.mark.parametrize("actor", ACTORS)
@pytest.mark.parametrize("resource,path", LIST_CASES)
def test_lists_exclude_deleted_and_foreign_resources(
    client, db, ownership_case, actor, resource, path,
):
    case = ownership_case
    deleted_id = mark_deleted(db, case, resource).id
    before = snapshot(db, case)
    response = client.get(path, headers=case[actor]["headers"])
    assert response.status_code == (401 if actor == "anonymous" else 200), response.text
    if actor != "anonymous":
        rows = response.json()
        assert deleted_id not in {row["id"] for row in rows}
        assert all(row["user_id"] == str(case[actor]["user"].id) for row in rows)
        if actor == "other":
            assert case["other"]["rows"][resource].id in {row["id"] for row in rows}
    assert snapshot(db, case) == before


@pytest.mark.parametrize("actor", ["owner", "other"])
@pytest.mark.parametrize("resource", list(REPOSITORIES))
def test_repository_ownership_queries_do_not_resurrect_deleted_rows(
    db, ownership_case, actor, resource,
):
    case = ownership_case
    row = mark_deleted(db, case, resource)
    before = snapshot(db, case)
    repo = REPOSITORIES[resource](db)
    assert repo.get_by_id(row.id) is None
    assert repo.get_by_id_and_user_id(row.id, case[actor]["user"].id) is None
    assert snapshot(db, case) == before
    assert db.get(RESOURCE_MODELS[resource], row.id) is not None


REFERENCE_CASES = [
    ("goal_task", "goals"), ("goal_workflow", "goals"), ("goal_list", "goals"),
    ("task_schedule", "tasks"), ("task_schedule_list", "tasks"), ("task_instance", "tasks"),
    ("schedule_instance", "task_schedules"),
    ("scheme_task", "scoring_schemes"), ("scheme_update", "scoring_schemes"),
    ("scheme_workflow", "scoring_schemes"),
    ("complete", "task_instances"), ("redemption", "rewards"), ("redeem", "rewards"),
]


@pytest.mark.parametrize("actor", ACTORS)
@pytest.mark.parametrize("action,resource", REFERENCE_CASES)
def test_nested_operations_and_workflows_reject_deleted_references(
    client, db, ownership_case, actor, action, resource,
):
    case = ownership_case
    ids = ids_for(case)
    actor_ids = ids_for(case, "owner" if actor == "anonymous" else actor)
    mark_deleted(db, case, resource)
    task = {"title": "Blocked task", "scoring_scheme_id": ids["scoring_schemes"]}
    instance_path = f"/tasks/{ids['tasks']}/task_schedules/{ids['task_schedules']}/task_instances"
    requests = {
        "goal_task": ("POST", f"/goals/{ids['goals']}/tasks", task),
        "goal_workflow": ("POST", f"/workflows/goals/{ids['goals']}/tasks", {"task": task}),
        "goal_list": ("GET", f"/goals/{ids['goals']}/tasks", None),
        "task_schedule": ("POST", f"/tasks/{ids['tasks']}/task_schedules", {
            "schedule_type": "daily", "schedule_value_json": {},
        }),
        "task_schedule_list": ("GET", f"/tasks/{ids['tasks']}/task_schedules", None),
        "task_instance": ("POST", instance_path, {"date_instance": "2046-05-11"}),
        "schedule_instance": ("POST", instance_path, {"date_instance": "2046-05-11"}),
        "scheme_task": ("POST", f"/goals/{actor_ids['goals']}/tasks", task),
        "scheme_update": ("POST", f"/tasks/{actor_ids['tasks']}", task),
        "scheme_workflow": ("POST", f"/workflows/goals/{actor_ids['goals']}/tasks", {"task": task}),
        "complete": ("POST", f"/task_instances/{ids['task_instances']}/complete", {
            "completion_level": "normal",
        }),
        "redemption": ("POST", "/redemptions", {"reward_id": ids["rewards"]}),
        "redeem": ("POST", f"/workflows/rewards/{ids['rewards']}/redeem", None),
    }
    before = snapshot(db, case)
    method, path, payload = requests[action]
    response = client.request(method, path, headers=case[actor]["headers"], json=payload)
    assert response.status_code == (401 if actor == "anonymous" else 404), response.text
    assert snapshot(db, case) == before


@pytest.mark.parametrize("actor", ACTORS)
@pytest.mark.parametrize("resource", ["goals", "tasks", "task_schedules", "scoring_schemes"])
@pytest.mark.parametrize("path", [
    "/task_instances?date=2045-05-10", "/task_instances/month?year=2045&month=5",
])
def test_retained_instance_history_still_belongs_only_to_its_owner(
    client, db, ownership_case, actor, resource, path,
):
    case = ownership_case
    mark_deleted(db, case, resource)
    before = snapshot(db, case)
    response = client.get(path, headers=case[actor]["headers"])
    assert response.status_code == (401 if actor == "anonymous" else 200), response.text
    if actor != "anonymous":
        rows = response.json()
        assert {row["id"] for row in rows} == {case[actor]["rows"]["task_instances"].id}
        assert all(row["user_id"] == str(case[actor]["user"].id) for row in rows)
    assert snapshot(db, case) == before


@pytest.mark.parametrize("actor", ACTORS)
@pytest.mark.parametrize("resource,owner_status", [
    ("goals", 404), ("tasks", 404), ("task_schedules", 200), ("scoring_schemes", 200),
])
def test_history_completion_preserves_parent_and_snapshot_rules(
    client, db, ownership_case, actor, resource, owner_status,
):
    case = ownership_case
    deleted = client.post(
        f"/{resource}/{ids_for(case)[resource]}/delete", headers=case["owner"]["headers"],
    )
    assert deleted.status_code == 204, deleted.text
    before = snapshot(db, case)
    response = client.post(
        f"/task_instances/{ids_for(case)['task_instances']}/complete",
        headers=case[actor]["headers"], json={"completion_level": "normal"},
    )
    want = owner_status if actor == "owner" else 401 if actor == "anonymous" else 404
    assert response.status_code == want, response.text
    if want != 200:
        assert snapshot(db, case) == before
    else:
        db.expire_all()
        assert case["owner"]["rows"]["task_instances"].score_awarded == 5
        assert case["owner"]["user"].current_value == 105
        assert case["other"]["user"].current_value == 200
        ledgers = PointLedgerRepository(db).list_by_user_id(case["owner"]["user"].id)
        assert len(ledgers) == 2
        assert sum(row.delta for row in ledgers) == 105


@pytest.mark.parametrize("resource", ["users", "goals", "tasks", "task_schedules"])
@pytest.mark.parametrize("entrypoint", ["http", "scheduler"])
def test_deleted_generation_parent_cannot_generate_instances(
    client, db, ownership_case, resource, entrypoint,
):
    case = ownership_case
    mark_deleted(db, case, resource)
    target = date(2046, 5, 12)
    before = snapshot(db, case)
    if entrypoint == "http":
        response = client.post(
            "/tasks_instances/generate", headers=case["owner"]["headers"],
            json={"date_instance": target.isoformat()},
        )
        assert response.status_code == (401 if resource == "users" else 201), response.text
        if resource != "users":
            assert response.json() == []
        assert snapshot(db, case) == before
    else:
        result = build_generate_task_instances_mediator(db).send(
            GenerateDailyTaskInstancesCommand(target_date=target),
        )
        assert ids_for(case)["tasks"] not in {row.task_id for row in result.task_instances}
        assert ids_for(case, "other")["tasks"] in {row.task_id for row in result.task_instances}
    assert db.query(TaskInstance).filter(
        TaskInstance.user_id == case["owner"]["user"].id,
        TaskInstance.date_instance == target,
    ).count() == 0


@pytest.mark.parametrize("actor", ["owner", "other"])
@pytest.mark.parametrize("action,resource", [
    ("complete", "task_instances"), ("redeem", "rewards"),
    ("task_goal", "goals"), ("task_scheme", "scoring_schemes"),
])
def test_direct_commands_cannot_bypass_deleted_resource_checks(
    db, ownership_case, actor, action, resource,
):
    case = ownership_case
    ids = ids_for(case)
    mark_deleted(db, case, resource)
    user_id = case[actor]["user"].id
    before = snapshot(db, case)
    with pytest.raises(NotFoundError):
        if action == "complete":
            build_complete_task_instance_mediator(db).send(CompleteTaskInstanceCommand(
                task_instance_id=ids["task_instances"], user_id=user_id, completion_level="normal",
            ))
        elif action == "redeem":
            build_redeem_reward_mediator(db).send(RedeemRewardCommand(
                reward_id=ids["rewards"], user_id=user_id,
            ))
        else:
            goal_id = ids["goals"] if action == "task_goal" else ids_for(case, actor)["goals"]
            build_create_task_with_schedule_mediator(db).send(CreateTaskWithScheduleCommand(
                goal_id=goal_id, user_id=user_id, payload=CreateTaskWithScheduleDTO(
                    task=CreateTaskDTO(title="Blocked", scoring_scheme_id=ids["scoring_schemes"]),
                ),
            ))
    assert snapshot(db, case) == before


@pytest.mark.parametrize("entrypoint", ["task", "workflow", "ai", "update"])
def test_deleted_public_default_is_rejected_without_partial_writes(
    client, db, ownership_case, monkeypatch, entrypoint,
):
    case = ownership_case
    scheme = ScoringScheme(
        user_id=None, title="Deleted public default", levels_json={"normal": 1},
        deleted_at=datetime.now(timezone.utc),
    )
    db.add(scheme)
    db.commit()
    monkeypatch.setattr("app.shared.function.SCORING_SCHME_ID", SimpleNamespace(DEFAULT=scheme.id))
    before = snapshot(db, case)
    path, payload = f"/goals/{ids_for(case)['goals']}/tasks", {"title": "Blocked default"}
    if entrypoint == "workflow":
        path, payload = f"/workflows/goals/{ids_for(case)['goals']}/tasks", {"task": payload}
    elif entrypoint == "ai":
        from ai_draft_support import save_draft
        draft_id = save_draft(db, case["owner"]["user"].id, {
            "goal_title": "Must roll back", "tasks": [{
                "title": "Blocked default", "schedule_type": "daily", "schedule_value_json": {},
            }],
        })
        path, payload = "/workflows/ai/confirm", {"draft_id": draft_id}
    elif entrypoint == "update":
        path = f"/tasks/{ids_for(case)['tasks']}"
        payload = {"scoring_scheme_id": scheme.id}
    response = client.post(path, headers=case["owner"]["headers"], json=payload)
    assert response.status_code == 404, response.text
    assert snapshot(db, case) == before
    db.refresh(scheme)
    assert scheme.deleted_at is not None


@pytest.mark.parametrize("actor", ACTORS)
@pytest.mark.parametrize("view", ["detail", "list"])
def test_deleted_reward_does_not_hide_or_expose_redemption_history(
    client, db, ownership_case, actor, view,
):
    case = ownership_case
    redemption = case["owner"]["rows"]["redemptions"]
    reward = db.get(Reward, redemption.reward_id)
    reward.deleted_at = datetime.now(timezone.utc)
    db.commit()
    before = snapshot(db, case)
    path = f"/redemptions/{redemption.id}" if view == "detail" else "/redemptions"
    response = client.get(path, headers=case[actor]["headers"])
    want = 401 if actor == "anonymous" else 404 if actor == "other" and view == "detail" else 200
    assert response.status_code == want, response.text
    if want == 200:
        rows = [response.json()] if view == "detail" else response.json()
        assert {row["id"] for row in rows} == {case[actor]["rows"]["redemptions"].id}
        assert all(row["user_id"] == str(case[actor]["user"].id) for row in rows)
    assert snapshot(db, case) == before


@pytest.mark.parametrize("actor", ACTORS)
@pytest.mark.parametrize("view", ["balance", "reconciliation"])
def test_deleted_ledger_is_excluded_without_repairing_cache_or_leaking_balance(
    client, db, ownership_case, actor, view,
):
    case = ownership_case
    mark_deleted(db, case, "point_ledgers")
    before = snapshot(db, case)
    response = client.get(f"/point_ledgers/{view}", headers=case[actor]["headers"])
    assert response.status_code == (401 if actor == "anonymous" else 200), response.text
    if actor != "anonymous":
        if view == "balance":
            assert response.json()["balance"] == (0 if actor == "owner" else 200)
        elif actor == "owner":
            assert response.json() == {
                "cached_balance": 100, "ledger_balance": 0, "difference": 100, "is_consistent": False,
            }
        else:
            assert response.json() == {
                "cached_balance": 200, "ledger_balance": 200, "difference": 0, "is_consistent": True,
            }
    assert snapshot(db, case) == before


@pytest.mark.parametrize("action", [
    "profile", "user", "goals", "tasks", "schedules", "instances", "complete",
    "scoring", "points", "reconciliation", "rewards", "redeem", "redemptions",
])
def test_deleted_users_old_token_cannot_access_or_operate_resources(
    client, db, ownership_case, action,
):
    case = ownership_case
    ids = ids_for(case)
    mark_deleted(db, case, "users")
    requests = {
        "profile": ("GET", "/users/me", None),
        "user": ("GET", f"/users/{ids['users']}", None),
        "goals": ("POST", f"/goals/{ids['goals']}", {"title": "Blocked"}),
        "tasks": ("POST", f"/tasks/{ids['tasks']}/delete", None),
        "schedules": ("GET", "/task_schedules", None),
        "instances": ("GET", "/task_instances?date=2045-05-10", None),
        "complete": ("POST", f"/task_instances/{ids['task_instances']}/complete", {"completion_level": "normal"}),
        "scoring": ("POST", f"/scoring_schemes/{ids['scoring_schemes']}", {"title": "Blocked"}),
        "points": ("POST", "/point_ledgers", {"delta": 10, "entry_type": "earn"}),
        "reconciliation": ("GET", "/point_ledgers/reconciliation", None),
        "rewards": ("GET", "/rewards", None),
        "redeem": ("POST", f"/workflows/rewards/{ids['rewards']}/redeem", None),
        "redemptions": ("GET", f"/redemptions/{ids['redemptions']}", None),
    }
    before = snapshot(db, case)
    method, path, payload = requests[action]
    response = client.request(method, path, headers=case["owner"]["headers"], json=payload)
    assert response.status_code == 401, response.text
    assert snapshot(db, case) == before
