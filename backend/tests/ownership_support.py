"""Shared real-model fixtures and persisted-state checks for security matrices."""

from copy import deepcopy
from datetime import date
from uuid import uuid4

import pytest

from app.auth.security import create_access_token
from app.goals.models import Goal
from app.point_ledgers.models import PointLedger
from app.redemptions.models import Redemption
from app.rewards.models import Reward
from app.scoring_schemes.models import ScoringScheme
from app.shared.enums import ScheduleType
from app.task_instances.models import TaskInstance
from app.task_schedules.models import TaskSchedule
from app.tasks.models import Task
from app.users.models import User


TARGET_DATE = date(2045, 5, 10)
RESOURCE_MODELS = {
    "goals": Goal, "tasks": Task, "task_schedules": TaskSchedule,
    "task_instances": TaskInstance, "scoring_schemes": ScoringScheme,
    "rewards": Reward, "redemptions": Redemption, "point_ledgers": PointLedger,
}
EDIT_CASES = [
    ("goals", {"title": "Changed", "start_date": "2045-05-10"}),
    ("tasks", {"title": "Changed"}),
    ("task_schedules", {
        "schedule_type": "daily", "schedule_value_json": {}, "end_date": "2045-06-01",
    }),
    ("scoring_schemes", {"title": "Changed"}),
    ("rewards", {"title": "Changed"}),
]
LIST_CASES = [(name, f"/{name}") for name in (
    "goals", "tasks", "task_schedules", "scoring_schemes", "rewards", "redemptions", "point_ledgers",
)] + [("task_instances", "/task_instances?date=2045-05-10"),
     ("task_instances", "/task_instances/month?year=2045&month=5")]


@pytest.fixture
def ownership_case(db):
    def make_actor(balance):
        user = User(
            email=f"ownership-{uuid4()}@example.com",
            password_hash="not-used", current_value=balance,
        )
        goal = Goal(user=user, title="Private goal", start_date=TARGET_DATE)
        scheme = ScoringScheme(user=user, title="Private scheme", levels_json={"normal": 5})
        task = Task(
            user=user, goal=goal, title="Private task", scoring_scheme=scheme,
            scoring_scheme_json={"normal": 5},
        )
        schedule = TaskSchedule(
            user=user, task=task, schedule_type=ScheduleType.DAILY,
            schedule_value_json={}, start_date=date(2020, 1, 1),
        )
        instance = TaskInstance(
            user=user, task=task, task_schedule=schedule,
            date_instance=TARGET_DATE, scoring_snapshot_json={"normal": 5},
        )
        reward = Reward(user=user, title="Private reward", cost_points=10)
        history_reward = Reward(user=user, title="Historical reward", cost_points=0)
        redemption = Redemption(
            user=user, reward=history_reward, cost_points=0,
            reward_snapshot_json={"title": "Historical reward", "cost_points": 0},
        )
        ledger = PointLedger(user=user, delta=balance, entry_type="earn", event_at=TARGET_DATE)
        db.add_all([user, goal, scheme, task, schedule, instance, reward, redemption, ledger])
        db.flush()
        rows = {
            "goals": goal, "tasks": task, "task_schedules": schedule,
            "task_instances": instance, "scoring_schemes": scheme, "rewards": reward,
            "redemptions": redemption, "point_ledgers": ledger,
        }
        return {
            "user": user, "rows": rows,
            "headers": {"Authorization": f"Bearer {create_access_token(sub=str(user.id))}"},
        }

    case = {"owner": make_actor(100), "other": make_actor(200), "anonymous": {"headers": {}}}
    db.commit()
    user_ids = [case[actor]["user"].id for actor in ("owner", "other")]
    yield case
    db.rollback()
    for model in (TaskInstance, PointLedger, Redemption, TaskSchedule, Task,
                  ScoringScheme, Goal, Reward):
        db.query(model).filter(model.user_id.in_(user_ids)).delete(synchronize_session=False)
    db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
    db.commit()


def snapshot(db, case):
    """Compare persisted columns, not ORM identities or an incomplete fake state."""
    db.expire_all()
    user_ids = [case[actor]["user"].id for actor in ("owner", "other")]
    result = {}
    for name, model in {"users": User, **RESOURCE_MODELS}.items():
        owner_column = model.id if model is User else model.user_id
        rows = db.query(model).filter(owner_column.in_(user_ids)).order_by(model.id).all()
        result[name] = [
            deepcopy({column.key: getattr(row, column.key) for column in model.__table__.columns})
            for row in rows
        ]
    return result


def ids_for(case, actor="owner"):
    return {
        **{name: row.id for name, row in case[actor]["rows"].items()},
        "users": case[actor]["user"].id,
    }
