from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.core.unit_of_work import build_unit_of_work
from app.goals.models import Goal
from app.goals.repository import GoalRepository
from app.point_ledgers.models import PointLedger
from app.point_ledgers.repository import PointLedgerRepository
from app.redemptions.models import Redemption
from app.redemptions.repository import RedemptionRepository
from app.rewards.models import Reward
from app.rewards.repository import RewardRepository
from app.scoring_schemes.models import ScoringScheme
from app.scoring_schemes.repository import ScoringSchemeRepository
from app.task_instances.dependencies import build_generate_task_instances_mediator
from app.task_instances.commands import GenerateDailyTaskInstancesCommand
from app.task_instances.models import TaskInstance
from app.task_instances.repository import TaskInstanceRepository
from app.task_schedules.models import TaskSchedule
from app.task_schedules.repository import TaskScheduleRepository
from app.tasks.models import Task
from app.tasks.repository import TaskRepository
from app.users.models import User
from app.users.repository import UserRepository


@pytest.mark.parametrize("resource,model,fixture_name,changes", [
    ("goals", Goal, "goal", {"title": "Changed", "start_date": "2026-03-14"}),
    ("tasks", Task, "task", {"title": "Changed"}),
    ("task_schedules", TaskSchedule, "task_schedule", {
        "schedule_type": "daily", "schedule_value_json": {},
    }),
    ("scoring_schemes", ScoringScheme, "scoring_scheme", {"title": "Changed"}),
    ("rewards", Reward, "reward", {"title": "Changed"}),
])
def test_delete_preserves_row_and_blocks_normal_access(
    client, auth_headers, db, request, resource, model, fixture_name, changes,
):
    item = request.getfixturevalue(fixture_name)
    path = f"/{resource}/{item['id']}"
    assert client.post(f"{path}/delete", headers=auth_headers).status_code == 204
    row = db.get(model, item["id"])
    assert row is not None
    assert row.deleted_at is not None
    repo = {
        "goals": GoalRepository, "tasks": TaskRepository,
        "task_schedules": TaskScheduleRepository,
        "scoring_schemes": ScoringSchemeRepository, "rewards": RewardRepository,
    }[resource](db)
    assert repo.get_by_id(item["id"]) is None
    assert repo.get_by_id_and_user_id(item["id"], row.user_id) is None
    assert client.get(path, headers=auth_headers).status_code == 404
    assert item["id"] not in {
        value["id"] for value in client.get(f"/{resource}", headers=auth_headers).json()
    }
    assert client.post(path, headers=auth_headers, json=changes).status_code == 404
    assert client.post(f"{path}/delete", headers=auth_headers).status_code == 404


@pytest.mark.parametrize("resource,fixture_name", [
    ("goals", "goal"), ("tasks", "task"), ("task_schedules", "task_schedule"),
])
def test_deleted_parent_stops_generation_without_erasing_history(
    client, auth_headers, db, request, task, task_schedule, task_instance,
    resource, fixture_name,
):
    item = request.getfixturevalue(fixture_name)
    assert client.post(
        f"/{resource}/{item['id']}/delete", headers=auth_headers,
    ).status_code == 204
    result = build_generate_task_instances_mediator(db).send(
        GenerateDailyTaskInstancesCommand(target_date=date(2040, 1, 10)),
    )
    assert task["id"] not in {instance.task_id for instance in result.task_instances}
    assert db.get(Task, task["id"]) is not None
    assert db.get(TaskSchedule, task_schedule["id"]) is not None
    assert db.get(TaskInstance, task_instance["id"]) is not None
    history = client.get("/task_instances?date=2026-04-16", headers=auth_headers)
    assert task_instance["id"] in {item["id"] for item in history.json()}
    assert client.get(
        f"/task_schedules/{task_schedule['id']}", headers=auth_headers,
    ).status_code == 404
    assert task_schedule["id"] not in {
        row["id"] for row in client.get("/task_schedules", headers=auth_headers).json()
    }
    assert client.post(
        f"/tasks/{task['id']}/task_schedules/{task_schedule['id']}/task_instances",
        headers=auth_headers, json={"date_instance": "2040-01-11"},
    ).status_code == 404
    if resource == "goals":
        assert client.get(f"/tasks/{task['id']}", headers=auth_headers).status_code == 404
        assert task["id"] not in {
            row["id"] for row in client.get("/tasks", headers=auth_headers).json()
        }


@pytest.mark.parametrize("resource,fixture_name", [("goals", "goal"), ("tasks", "task")])
def test_deleted_task_cannot_change_earned_points(
    client, auth_headers, db, request, task_instance, resource, fixture_name,
):
    path = f"/task_instances/{task_instance['id']}/complete"
    completed = client.post(path, headers=auth_headers, json={"completion_level": "normal"})
    assert completed.status_code == 200
    user_id = UUID(task_instance["user_id"])
    before = db.get(User, user_id).current_value
    ledger_ids = {row.id for row in PointLedgerRepository(db).list_by_user_id(user_id)}
    item = request.getfixturevalue(fixture_name)
    assert client.post(f"/{resource}/{item['id']}/delete", headers=auth_headers).status_code == 204
    assert client.post(path, headers=auth_headers, json={"completion_level": "perfect"}).status_code == 404
    assert db.get(User, user_id).current_value == before
    assert {row.id for row in PointLedgerRepository(db).list_by_user_id(user_id)} == ledger_ids
    assert db.get(TaskInstance, task_instance["id"]).score_awarded == 1


def test_deleted_scoring_scheme_rejected_for_new_tasks_but_snapshots_still_work(
    client, auth_headers, goal, scoring_scheme, task_instance,
):
    assert client.post(
        f"/scoring_schemes/{scoring_scheme['id']}/delete", headers=auth_headers,
    ).status_code == 204
    assert client.post(
        f"/goals/{goal['id']}/tasks", headers=auth_headers,
        json={"title": "Blocked", "scoring_scheme_id": scoring_scheme["id"]},
    ).status_code == 404
    assert client.post(
        f"/task_instances/{task_instance['id']}/complete", headers=auth_headers,
        json={"completion_level": "normal"},
    ).status_code == 200


def test_deleted_reward_keeps_redemption_history_and_blocks_new_redemptions(
    client, auth_headers, db, reward, redemption,
):
    user_id = UUID(reward["user_id"])
    before = db.get(User, user_id).current_value
    assert client.post(f"/rewards/{reward['id']}/delete", headers=auth_headers).status_code == 204
    assert client.get(f"/redemptions/{redemption['id']}", headers=auth_headers).status_code == 200
    assert client.post(
        "/redemptions", headers=auth_headers, json={"reward_id": reward["id"]},
    ).status_code == 404
    assert RewardRepository(db).get_available_reward_by_id_and_user_id(reward["id"], user_id) is None
    assert db.get(User, user_id).current_value == before


def test_cannot_assign_deleted_scoring_scheme_when_updating_task(
    client, auth_headers, task, scoring_scheme,
):
    assert client.post(
        f"/scoring_schemes/{scoring_scheme['id']}/delete", headers=auth_headers,
    ).status_code == 204
    assert client.post(
        f"/tasks/{task['id']}", headers=auth_headers,
        json={"scoring_scheme_id": scoring_scheme["id"]},
    ).status_code == 404
    assert client.post(
        f"/tasks/{task['id']}", headers=auth_headers, json={"title": "Still editable"},
    ).status_code == 200


def test_soft_deleted_instance_is_hidden_and_can_be_generated_again(
    client, auth_headers, db, task_instance,
):
    old = db.get(TaskInstance, task_instance["id"])
    old.deleted_at = datetime.now(timezone.utc)
    db.commit()
    repo = TaskInstanceRepository(db)
    assert repo.get_by_id(old.id) is None
    assert repo.get_by_id_and_user_id(old.id, old.user_id) is None
    assert repo.get_by_id_and_user_id_for_update(old.id, old.user_id) is None
    assert repo.get_by_task_id_and_date_instance(old.task_id, old.date_instance) is None
    for rows in (
        repo.list_by_task_id(old.task_id), repo.list_by_user_id(old.user_id),
        repo.list_by_user_id_and_date(old.user_id, old.date_instance),
        repo.list_by_user_id_between_date(old.user_id, old.date_instance, old.date_instance),
    ):
        assert old.id not in {row.id for row in rows}
    assert client.post(
        f"/task_instances/{old.id}/complete", headers=auth_headers,
        json={"completion_level": "normal"},
    ).status_code == 404
    result = build_generate_task_instances_mediator(db).send(
        GenerateDailyTaskInstancesCommand(target_date=old.date_instance),
    )
    replacement = next(row for row in result.task_instances if row.task_id == old.task_id)
    assert replacement.id != old.id
    assert replacement.deleted_at is None
    assert db.get(TaskInstance, old.id).deleted_at is not None


def test_deleted_user_cannot_authenticate_and_email_stays_reserved(client, db):
    credentials = {"email": f"deleted-{uuid4()}@example.com", "password": "password123"}
    assert client.post("/auth/signup", json=credentials).status_code == 201
    token = client.post("/auth/login", json=credentials).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_id = UUID(client.get("/users/me", headers=headers).json()["id"])
    user = db.get(User, user_id)
    user.deleted_at = datetime.now(timezone.utc)
    db.commit()
    assert UserRepository(db).get_by_id(user_id) is None
    assert UserRepository(db).get_by_email(credentials["email"]) is None
    assert client.get("/users/me", headers=headers).status_code == 401
    assert client.post("/auth/login", json=credentials).status_code == 401
    assert client.post("/auth/signup", json=credentials).status_code == 409


def test_financial_queries_exclude_soft_deleted_rows(db, auth_user, redemption):
    user_id = UUID(auth_user["user_id"])
    ledger = PointLedger(
        user_id=user_id, delta=1000, entry_type="earn", source_type="test",
        event_at=date.today(), deleted_at=datetime.now(timezone.utc),
    )
    db.add(ledger)
    redeemed = db.get(Redemption, redemption["id"])
    redeemed.deleted_at = datetime.now(timezone.utc)
    db.flush()
    ledger_repo = PointLedgerRepository(db)
    assert ledger_repo.get_by_id(ledger.id) is None
    assert ledger_repo.get_by_id_and_user_id(ledger.id, user_id) is None
    visible = ledger_repo.list_by_user_id(user_id)
    assert ledger.id not in {row.id for row in visible}
    assert ledger_repo.get_balance_by_user_id(user_id) == sum(row.delta for row in visible)
    redemption_repo = RedemptionRepository(db)
    assert redemption_repo.get_by_id(redeemed.id) is None
    assert redemption_repo.get_by_id_and_user_id(redeemed.id, user_id) is None
    assert redeemed.id not in {row.id for row in redemption_repo.list_by_user_id(user_id)}


def test_soft_delete_rolls_back_with_unit_of_work(db, goal):
    repo = GoalRepository(db)
    with pytest.raises(RuntimeError, match="abort"):
        with build_unit_of_work(db).begin():
            row = db.get(Goal, goal["id"])
            repo.delete(row)
            assert row.deleted_at is not None
            assert repo.get_by_id(goal["id"]) is None
            raise RuntimeError("abort")
    assert repo.get_by_id(goal["id"]).deleted_at is None
