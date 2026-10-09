from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.security import create_access_token
from app.core.unit_of_work import build_unit_of_work
from app.errors.exception import ConflictError
from app.point_ledgers.models import PointLedger
from app.redemptions.models import Redemption
from app.rewards.models import Reward
from app.users.models import User
from app.workflows.redemption_workflow.dependencies import build_redemption_workflow_service


@pytest.fixture
def redemption_case(db):
    user = User(email=f"concurrency-{uuid4()}@example.com", password_hash="unused", current_value=100)
    db.add(user)
    db.flush()
    rewards = [Reward(user_id=user.id, title=f"Reward {i}", cost_points=60) for i in range(2)]
    db.add_all(rewards)
    db.add(PointLedger(user_id=user.id, delta=100, entry_type="earn", source_type="test_funding"))
    db.commit()
    case = {"user_id": user.id, "reward_ids": [row.id for row in rewards]}
    db.rollback()
    return case


def _headers(user_id):
    return {"Authorization": f"Bearer {create_access_token(sub=str(user_id))}"}


@pytest.mark.parametrize("same_reward", [True, False])
@pytest.mark.parametrize("entrypoint", ["service", "command"])
def test_parallel_redemptions_do_not_duplicate_or_overspend(db, redemption_case, same_reward, entrypoint):
    case = redemption_case
    bind = db.get_bind()
    barrier = Barrier(2)
    reward_ids = case["reward_ids"][:1] * 2 if same_reward else case["reward_ids"]

    def redeem(reward_id):
        with Session(bind) as session:
            session.execute(text("SET LOCAL lock_timeout = '5s'"))
            # Authentication/earlier reads may already have cached these rows.
            cached_user = session.get(User, case["user_id"])
            cached_reward = session.get(Reward, reward_id)
            assert cached_user.current_value == 100
            assert cached_reward.status == "available"
            barrier.wait(timeout=10)
            try:
                if entrypoint == "command":
                    from app.workflows.redemption_workflow.commands import RedeemRewardCommand
                    from app.workflows.redemption_workflow.dependencies import build_redeem_reward_mediator

                    build_redeem_reward_mediator(session).send(RedeemRewardCommand(
                        reward_id=reward_id, user_id=case["user_id"],
                    ))
                else:
                    with build_unit_of_work(session).begin():
                        build_redemption_workflow_service(session).redemption_workflow(
                            reward_id=reward_id, user_id=case["user_id"],
                        )
                return "success"
            except ConflictError:
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(redeem, reward_id) for reward_id in reward_ids]
        outcomes = [future.result(timeout=15) for future in futures]
    assert sorted(outcomes) == ["conflict", "success"]
    with Session(bind) as reader:
        assert reader.get(User, case["user_id"]).current_value == 40
        redemptions = reader.query(Redemption).filter(Redemption.user_id == case["user_id"]).all()
        assert len(redemptions) == 1
        spent = reader.query(PointLedger).filter(
            PointLedger.user_id == case["user_id"], PointLedger.source_type == "redemption",
        ).all()
        assert len(spent) == 1
        assert spent[0].delta == -60
        assert spent[0].source_id == redemptions[0].id
        states = [reader.get(Reward, reward_id).status for reward_id in case["reward_ids"]]
        assert sorted(states) == ["available", "redeemed"]


def test_redemption_rechecks_balance_even_when_user_is_already_cached(db, redemption_case):
    case = redemption_case
    with Session(db.get_bind()) as session:
        cached = session.get(User, case["user_id"])
        assert cached.current_value == 100
        with Session(db.get_bind()) as writer:
            writer.get(User, case["user_id"]).current_value = 40
            writer.commit()
        with pytest.raises(ConflictError), build_unit_of_work(session).begin():
            build_redemption_workflow_service(session).redemption_workflow(
                reward_id=case["reward_ids"][0], user_id=case["user_id"],
            )
    with Session(db.get_bind()) as reader:
        assert reader.get(User, case["user_id"]).current_value == 40
        assert reader.query(Redemption).filter(Redemption.user_id == case["user_id"]).count() == 0


def test_repeated_redemption_returns_conflict_without_charging_twice(client, db, redemption_case):
    case = redemption_case
    path = f"/workflows/rewards/{case['reward_ids'][0]}/redeem"
    assert client.post(path, headers=_headers(case["user_id"])).status_code == 200
    response = client.post(path, headers=_headers(case["user_id"]))
    assert response.status_code == 409
    assert response.json()["code"] == "CONFLICT"
    with Session(db.get_bind()) as reader:
        assert reader.get(User, case["user_id"]).current_value == 40
        assert reader.query(Redemption).filter(Redemption.user_id == case["user_id"]).count() == 1


def test_redemption_rechecks_reward_even_when_already_cached(db, redemption_case):
    case = redemption_case
    reward_id = case["reward_ids"][0]
    with Session(db.get_bind()) as session:
        cached = session.get(Reward, reward_id)
        assert cached.status == "available"
        with Session(db.get_bind()) as writer:
            writer.get(Reward, reward_id).status = "redeemed"
            writer.commit()
        with pytest.raises(ConflictError), build_unit_of_work(session).begin():
            build_redemption_workflow_service(session).redemption_workflow(
                reward_id=reward_id, user_id=case["user_id"],
            )
    with Session(db.get_bind()) as reader:
        assert reader.get(User, case["user_id"]).current_value == 100
        assert reader.query(Redemption).filter(Redemption.user_id == case["user_id"]).count() == 0


@pytest.mark.parametrize("unavailable", ["deleted", "foreign"])
def test_locked_reward_lookup_keeps_ownership_and_soft_delete_checks(client, db, redemption_case, unavailable):
    case = redemption_case
    reward_id = case["reward_ids"][0]
    reward = db.get(Reward, reward_id)
    if unavailable == "deleted":
        reward.deleted_at = datetime.now(timezone.utc)
    else:
        other = User(email=f"other-{uuid4()}@example.com", password_hash="unused")
        db.add(other)
        db.flush()
        reward.user_id = other.id
    db.commit()
    response = client.post(
        f"/workflows/rewards/{reward_id}/redeem", headers=_headers(case["user_id"]),
    )
    assert response.status_code == 404
    with Session(db.get_bind()) as reader:
        assert reader.get(User, case["user_id"]).current_value == 100
        assert reader.query(Redemption).filter(Redemption.user_id == case["user_id"]).count() == 0


def test_redemption_rejects_insufficient_points_without_partial_writes(client, db, redemption_case):
    case = redemption_case
    db.get(User, case["user_id"]).current_value = 40
    db.commit()
    response = client.post(
        f"/workflows/rewards/{case['reward_ids'][0]}/redeem", headers=_headers(case["user_id"]),
    )
    assert response.status_code == 409
    with Session(db.get_bind()) as reader:
        assert reader.get(User, case["user_id"]).current_value == 40
        assert reader.get(Reward, case["reward_ids"][0]).status == "available"
        assert reader.query(Redemption).filter(Redemption.user_id == case["user_id"]).count() == 0
        assert reader.query(PointLedger).filter(PointLedger.user_id == case["user_id"]).count() == 1


@pytest.mark.parametrize("deleted", [False, True])
def test_database_rejects_duplicate_reward_redemption_even_after_soft_delete(db, redemption_case, deleted):
    case = redemption_case
    values = {"user_id": case["user_id"], "reward_id": case["reward_ids"][0],
              "cost_points": 60, "reward_snapshot_json": {}}
    db.add(Redemption(**values, deleted_at=datetime.now(timezone.utc) if deleted else None))
    db.commit()
    with pytest.raises(IntegrityError), build_unit_of_work(db).begin():
        db.add(Redemption(**values))
        db.flush()
    assert db.query(Redemption).filter(Redemption.reward_id == case["reward_ids"][0]).count() == 1


def test_duplicate_direct_redemption_returns_conflict_and_workflow_rolls_back(client, db, redemption_case):
    case = redemption_case
    headers = _headers(case["user_id"])
    reward_id = case["reward_ids"][0]
    assert client.post("/redemptions", headers=headers, json={"reward_id": reward_id}).status_code == 201
    assert client.post("/redemptions", headers=headers, json={"reward_id": reward_id}).status_code == 409
    assert client.post(f"/workflows/rewards/{reward_id}/redeem", headers=headers).status_code == 409
    with Session(db.get_bind()) as reader:
        assert reader.get(User, case["user_id"]).current_value == 100
        assert reader.get(Reward, reward_id).status == "available"
        assert reader.query(Redemption).filter(Redemption.reward_id == reward_id).count() == 1
        assert reader.query(PointLedger).filter(PointLedger.user_id == case["user_id"]).count() == 1
