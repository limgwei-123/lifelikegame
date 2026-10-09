from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.security import create_access_token
from app.core.unit_of_work import build_unit_of_work
from app.errors.exception import NotFoundError
from app.goals.models import Goal
from app.point_ledgers.dependencies import build_point_ledger_service
from app.point_ledgers.models import PointLedger
from app.point_ledgers.repository import PointLedgerRepository
from app.point_ledgers.schemas import CreatePointLedgerRequest
from app.rewards.models import Reward
from app.task_instances.models import TaskInstance
from app.task_schedules.models import TaskSchedule
from app.tasks.models import Task
from app.shared.enums import ScheduleType
from app.users.models import User
from app.users.repository import UserRepository


@pytest.fixture
def points_user(db):
    user = User(email=f"points-{uuid4()}@example.com", password_hash="unused")
    db.add(user)
    db.commit()
    user_id = user.id
    db.rollback()
    return {
        "user_id": user_id,
        "headers": {"Authorization": f"Bearer {create_access_token(sub=str(user_id))}"},
    }


@pytest.fixture
def points_task(db, points_user):
    user_id = points_user["user_id"]
    goal = Goal(user_id=user_id, title="Points goal")
    db.add(goal)
    db.flush()
    task = Task(user_id=user_id, goal_id=goal.id, title="Points task")
    db.add(task)
    db.flush()
    schedule = TaskSchedule(
        user_id=user_id, task_id=task.id, schedule_type=ScheduleType.DAILY,
        schedule_value_json={},
    )
    db.add(schedule)
    db.flush()
    instance = TaskInstance(
        user_id=user_id, task_id=task.id, task_schedule_id=schedule.id,
        date_instance=date(2026, 10, 9), scoring_snapshot_json={"normal": 10, "perfect": 25},
    )
    db.add(instance)
    db.commit()
    instance_id = instance.id
    db.rollback()
    return instance_id


def _payload(delta):
    return {"delta": delta, "entry_type": "adjustment", "source_type": "test"}


def _state(db, user_id):
    with Session(db.get_bind()) as reader:
        return (
            reader.get(User, user_id).current_value,
            [row.delta for row in reader.query(PointLedger).filter(
                PointLedger.user_id == user_id,
            ).order_by(PointLedger.id).all()],
        )


def test_direct_ledger_writes_update_the_cached_balance_once(client, db, points_user):
    headers = points_user["headers"]
    assert client.post("/point_ledgers", headers=headers, json=_payload(100)).status_code == 201
    assert _state(db, points_user["user_id"]) == (100, [100])
    assert client.post("/point_ledgers", headers=headers, json=_payload(-30)).status_code == 201
    assert _state(db, points_user["user_id"]) == (70, [100, -30])
    assert client.get("/point_ledgers/balance", headers=headers).json() == {"balance": 70}


def test_ledger_posting_without_optional_source_still_commits_both_writes(client, db, points_user):
    response = client.post("/point_ledgers", headers=points_user["headers"],
                           json={"delta": 10, "entry_type": "adjustment"})
    assert response.status_code == 201
    assert response.json()["source_type"] is None
    assert _state(db, points_user["user_id"]) == (10, [10])


@pytest.mark.parametrize("repository,method_name", [
    (PointLedgerRepository, "create"), (UserRepository, "update_user_point"),
])
def test_direct_ledger_failure_rolls_back_both_writes(
    client, db, points_user, monkeypatch, repository, method_name,
):
    original = getattr(repository, method_name)

    def fail_after_flush(self, *args, **kwargs):
        original(self, *args, **kwargs)
        raise RuntimeError("injected points failure")

    with monkeypatch.context() as patch:
        patch.setattr(repository, method_name, fail_after_flush)
        with pytest.raises(RuntimeError, match="injected points failure"):
            client.post("/point_ledgers", headers=points_user["headers"], json=_payload(10))
    assert _state(db, points_user["user_id"]) == (0, [])
    assert client.post("/point_ledgers", headers=points_user["headers"], json=_payload(10)).status_code == 201
    assert _state(db, points_user["user_id"]) == (10, [10])


def test_ledger_service_leaves_commit_to_the_callers_unit_of_work(db, points_user):
    with Session(db.get_bind()) as session:
        build_point_ledger_service(session).create_point_ledger(
            user_id=points_user["user_id"], payload=CreatePointLedgerRequest(**_payload(10)),
        )
        assert session.get(User, points_user["user_id"]).current_value == 10
        assert _state(db, points_user["user_id"]) == (0, [])
        session.rollback()
    assert _state(db, points_user["user_id"]) == (0, [])


def test_completion_changes_and_retries_keep_balance_equal_to_ledger(client, db, points_user, points_task):
    path = f"/task_instances/{points_task}/complete"
    for level, expected_balance, expected_deltas in [
        ("normal", 10, [10]), ("perfect", 25, [10, 15]),
        ("perfect", 25, [10, 15]), ("normal", 10, [10, 15, -15]),
    ]:
        response = client.post(path, headers=points_user["headers"], json={"completion_level": level})
        assert response.status_code == 200
        assert _state(db, points_user["user_id"]) == (expected_balance, expected_deltas)


def test_completion_balance_failure_rolls_back_instance_and_ledger(
    client, db, points_user, points_task, monkeypatch,
):
    original = UserRepository.update_user_point

    def fail_after_balance_update(self, *args, **kwargs):
        original(self, *args, **kwargs)
        raise RuntimeError("injected balance failure")

    with monkeypatch.context() as patch:
        patch.setattr(UserRepository, "update_user_point", fail_after_balance_update)
        with pytest.raises(RuntimeError, match="injected balance failure"):
            client.post(f"/task_instances/{points_task}/complete", headers=points_user["headers"],
                        json={"completion_level": "normal"})
    assert _state(db, points_user["user_id"]) == (0, [])
    with Session(db.get_bind()) as reader:
        instance = reader.get(TaskInstance, points_task)
        assert instance.status == "todo"
        assert instance.score_awarded == 0


def test_redemption_spends_ledger_funding_without_a_second_balance_debit(client, db, points_user):
    assert client.post("/point_ledgers", headers=points_user["headers"], json=_payload(100)).status_code == 201
    reward = Reward(user_id=points_user["user_id"], title="Funded reward", cost_points=30)
    db.add(reward)
    db.commit()
    response = client.post(f"/workflows/rewards/{reward.id}/redeem", headers=points_user["headers"])
    assert response.status_code == 200
    assert response.json()["remaining_points"] == 70
    assert _state(db, points_user["user_id"]) == (70, [100, -30])


def test_parallel_ledger_writes_keep_cache_and_ledger_consistent(db, points_user):
    barrier = Barrier(2)

    def add_points(delta):
        with Session(db.get_bind()) as session:
            session.execute(text("SET LOCAL lock_timeout = '5s'"))
            barrier.wait(timeout=10)
            with build_unit_of_work(session).begin():
                build_point_ledger_service(session).create_point_ledger(
                    user_id=points_user["user_id"], payload=CreatePointLedgerRequest(**_payload(delta)),
                )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(add_points, delta) for delta in (10, 20)]
        for future in futures:
            future.result(timeout=15)
    balance, deltas = _state(db, points_user["user_id"])
    assert balance == 30
    assert sorted(deltas) == [10, 20]


@pytest.mark.parametrize("cached,expected_difference,expected_consistent", [
    (15, 0, True), (99, 84, False), (None, None, False),
])
def test_reconciliation_reports_drift_without_repairing_history(
    client, db, points_user, cached, expected_difference, expected_consistent,
):
    user_id = points_user["user_id"]
    db.add_all([
        PointLedger(user_id=user_id, delta=20, entry_type="earn", source_type="test"),
        PointLedger(user_id=user_id, delta=-5, entry_type="redeem", source_type="test"),
        PointLedger(user_id=user_id, delta=1000, entry_type="earn", source_type="test",
                    deleted_at=datetime.now(timezone.utc)),
    ])
    db.flush()
    # Raw historical data deliberately bypasses the normal posting service.
    db.get(User, user_id).current_value = cached
    db.commit()
    response = client.get("/point_ledgers/reconciliation", headers=points_user["headers"])
    assert response.status_code == 200
    assert response.json() == {
        "cached_balance": cached, "ledger_balance": 15,
        "difference": expected_difference, "is_consistent": expected_consistent,
    }
    assert _state(db, user_id) == (cached, [20, -5, 1000])
    assert client.get("/point_ledgers/balance", headers=points_user["headers"]).json() == {"balance": 15}


def test_reconciliation_for_new_user_is_zero_and_does_not_include_other_users(client, db, points_user):
    other = User(email=f"other-points-{uuid4()}@example.com", password_hash="unused", current_value=500)
    db.add(other)
    db.flush()
    db.add(PointLedger(user_id=other.id, delta=500, entry_type="earn", source_type="test"))
    db.commit()
    response = client.get(
        f"/point_ledgers/reconciliation?user_id={other.id}", headers=points_user["headers"],
    )
    assert response.status_code == 200
    assert response.json() == {
        "cached_balance": 0, "ledger_balance": 0, "difference": 0, "is_consistent": True,
    }


@pytest.mark.parametrize("deleted", [False, True])
def test_points_operations_reject_missing_or_deleted_user(db, points_user, deleted):
    user_id = uuid4()
    if deleted:
        user_id = points_user["user_id"]
        db.get(User, user_id).deleted_at = datetime.now(timezone.utc)
        db.commit()
    service = build_point_ledger_service(db)
    with pytest.raises(NotFoundError), build_unit_of_work(db).begin():
        service.create_point_ledger(user_id=user_id, payload=CreatePointLedgerRequest(**_payload(10)))
    with pytest.raises(NotFoundError):
        service.get_balance_reconciliation(user_id=user_id)


def test_reconciliation_requires_a_live_authenticated_user(client, db, points_user):
    assert client.get("/point_ledgers/reconciliation").status_code == 401
    db.get(User, points_user["user_id"]).deleted_at = datetime.now(timezone.utc)
    db.commit()
    assert client.get("/point_ledgers/reconciliation", headers=points_user["headers"]).status_code == 401
