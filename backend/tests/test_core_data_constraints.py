from uuid import uuid4

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.redemptions.models import Redemption
from app.rewards.models import Reward
from app.task_instances.models import TaskInstance
from app.task_schedules.models import TaskSchedule
from app.users.models import User
from ownership_support import RESOURCE_MODELS


@pytest.mark.parametrize("resource,field,value,pgcode", [
    ("rewards", "cost_points", -1, "23514"),
    ("rewards", "status", "invalid", "23514"),
    ("rewards", "status", None, "23502"),
    ("redemptions", "cost_points", -1, "23514"),
    ("task_instances", "status", "completed", "23514"),
    ("task_instances", "status", None, "23502"),
])
def test_database_rejects_invalid_costs_and_states(db, ownership_case, resource, field, value, pgcode):
    row = ownership_case["owner"]["rows"][resource]
    row_id, previous = row.id, getattr(row, field)
    model = RESOURCE_MODELS[resource]
    with Session(db.get_bind()) as writer:
        with pytest.raises(IntegrityError) as error:
            writer.execute(update(model).where(model.id == row_id).values(**{field: value}))
            writer.commit()
        assert error.value.orig.pgcode == pgcode
        writer.rollback()
    with Session(db.get_bind()) as reader:
        assert getattr(reader.get(model, row_id), field) == previous


@pytest.mark.parametrize("change", [
    {"cost_points": -1}, {"cost_points": None}, {"cost_points": True},
    {"status": "invalid"}, {"status": None},
])
def test_reward_update_rejects_invalid_values_before_database_write(client, db, ownership_case, change):
    owner = ownership_case["owner"]
    reward_id = owner["rows"]["rewards"].id
    response = client.post(f"/rewards/{reward_id}", headers=owner["headers"], json=change)
    assert response.status_code == 422, response.text
    with Session(db.get_bind()) as reader:
        reward = reader.get(Reward, reward_id)
        assert reward.cost_points == 10
        assert reward.status == "available"


@pytest.mark.parametrize("cost", [-1, True])
def test_reward_creation_rejects_invalid_cost(client, db, ownership_case, cost):
    owner = ownership_case["owner"]
    user_id = owner["user"].id
    with Session(db.get_bind()) as reader:
        before = reader.query(Reward).filter_by(user_id=user_id).count()
    response = client.post("/rewards", headers=owner["headers"],
                           json={"title": "Invalid cost", "cost_points": cost})
    assert response.status_code == 422, response.text
    with Session(db.get_bind()) as reader:
        assert reader.query(Reward).filter_by(user_id=user_id).count() == before


def test_zero_cost_reward_and_omitted_update_fields_remain_valid(client, db, ownership_case):
    owner = ownership_case["owner"]
    response = client.post("/rewards", headers=owner["headers"], json={"title": "Free", "cost_points": 0})
    assert response.status_code == 201, response.text
    reward_id = response.json()["id"]
    changed = client.post(f"/rewards/{reward_id}", headers=owner["headers"], json={"description": "Edited"})
    assert changed.status_code == 200, changed.text
    with Session(db.get_bind()) as reader:
        reward = reader.get(Reward, reward_id)
        assert (reward.cost_points, reward.status, reward.description) == (0, "available", "Edited")
    for change in ({"cost_points": 1}, {"cost_points": 0}, {"status": "redeemed"}, {"status": "available"}):
        response = client.post(f"/rewards/{reward_id}", headers=owner["headers"], json=change)
        assert response.status_code == 200, response.text
        with Session(db.get_bind()) as reader:
            saved = reader.get(Reward, reward_id)
            assert all(getattr(saved, field) == value for field, value in change.items())


@pytest.mark.parametrize("resource,field,value", [
    ("rewards", "user_id", uuid4()), ("tasks", "goal_id", -1),
    ("task_schedules", "task_id", -1), ("task_instances", "task_schedule_id", -1),
    ("redemptions", "reward_id", -1),
])
def test_database_foreign_keys_reject_missing_parents(db, ownership_case, resource, field, value):
    model = RESOURCE_MODELS[resource]
    row_id = ownership_case["owner"]["rows"][resource].id
    with Session(db.get_bind()) as writer:
        with pytest.raises(IntegrityError) as error:
            writer.execute(update(model).where(model.id == row_id).values(**{field: value}))
            writer.commit()
        assert error.value.orig.pgcode == "23503"
        writer.rollback()


def test_database_reward_delete_preserves_referenced_history(db, ownership_case):
    owner = ownership_case["owner"]
    row_id = owner["rows"]["redemptions"].reward_id
    history_id = owner["rows"]["redemptions"].id
    with Session(db.get_bind()) as writer:
        with pytest.raises(IntegrityError) as error:
            writer.execute(delete(Reward).where(Reward.id == row_id))
            writer.commit()
        assert error.value.orig.pgcode == "23503"
        writer.rollback()
    with Session(db.get_bind()) as reader:
        assert reader.get(Reward, row_id) is not None
        assert reader.get(Redemption, history_id) is not None


def test_database_schedule_delete_cascades_instances_without_deleting_user(db, ownership_case):
    owner = ownership_case["owner"]
    schedule_id = owner["rows"]["task_schedules"].id
    instance_id = owner["rows"]["task_instances"].id
    user_id = owner["user"].id
    with Session(db.get_bind()) as writer:
        writer.execute(delete(TaskSchedule).where(TaskSchedule.id == schedule_id))
        writer.commit()
    with Session(db.get_bind()) as reader:
        assert reader.get(TaskSchedule, schedule_id) is None
        assert reader.get(TaskInstance, instance_id) is None
        assert reader.get(User, user_id) is not None


def test_database_user_cascade_removes_only_the_deleted_users_rows(db, ownership_case):
    owner_id, other_id = [ownership_case[actor]["user"].id for actor in ("owner", "other")]
    with Session(db.get_bind()) as writer:
        writer.execute(delete(User).where(User.id == owner_id))
        writer.commit()
    with Session(db.get_bind()) as reader:
        assert reader.get(User, owner_id) is None
        assert reader.get(User, other_id) is not None
        for model in RESOURCE_MODELS.values():
            assert reader.scalar(select(model.id).where(model.user_id == owner_id)) is None
            assert reader.scalar(select(model.id).where(model.user_id == other_id)) is not None
