from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.main import app
from app.point_ledgers.models import PointLedger
from app.point_ledgers.repository import PointLedgerRepository
from app.redemptions.models import Redemption
from app.redemptions.repository import RedemptionRepository
from app.rewards.models import Reward
from app.rewards.repository import RewardRepository
from app.users.models import User
from app.users.repository import UserRepository


def _persisted_state(bind, user_id, reward_id):
    with Session(bind) as reader:
        return {
            "balance": reader.get(User, user_id).current_value,
            "reward_status": reader.get(Reward, reward_id).status,
            "redemptions": [
                (row.id, row.cost_points, row.reward_snapshot_json)
                for row in reader.query(Redemption).filter(
                    Redemption.reward_id == reward_id,
                ).order_by(Redemption.id).all()
            ],
            "ledgers": [
                (row.id, row.delta, row.entry_type, row.source_type, row.source_id)
                for row in reader.query(PointLedger).filter(
                    PointLedger.user_id == user_id,
                ).order_by(PointLedger.id).all()
            ],
        }


@pytest.fixture
def funded_redemption(client, auth_headers, reward, db, monkeypatch):
    # Keep the test database session, but exercise the production UoW dependency.
    monkeypatch.delitem(app.dependency_overrides, get_db)
    user_id = UUID(reward["user_id"])
    user = db.get(User, user_id)
    user.current_value += 100
    db.get(Reward, reward["id"]).cost_points = 30
    db.add(PointLedger(
        user_id=user_id, delta=100, entry_type="earn", source_type="test_funding",
    ))
    db.commit()
    return {
        "user_id": user_id,
        "reward_id": reward["id"],
        "path": f"/workflows/rewards/{reward['id']}/redeem",
        "before": _persisted_state(db.get_bind(), user_id, reward["id"]),
    }


def test_successful_redemption_commits_balance_reward_redemption_and_ledger(
    client, auth_headers, db, funded_redemption,
):
    case = funded_redemption
    response = client.post(case["path"], headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["reward_id"] == case["reward_id"]
    assert data["cost_points"] == 30
    assert data["remaining_points"] == case["before"]["balance"] - 30
    after = _persisted_state(db.get_bind(), case["user_id"], case["reward_id"])
    assert after["balance"] == case["before"]["balance"] - 30
    assert after["reward_status"] == "redeemed"
    assert after["redemptions"] == [(data["redemption_id"], 30, {
        "id": case["reward_id"], "title": "First Reward",
        "description": None, "cost_points": 30,
    })]
    assert len(after["ledgers"]) == len(case["before"]["ledgers"]) + 1
    assert after["ledgers"][:-1] == case["before"]["ledgers"]
    assert after["ledgers"][-1][1:] == (-30, "redeem", "redemption", data["redemption_id"])


@pytest.mark.parametrize("repository,method_name", [
    (UserRepository, "update_user_point"),
    (RewardRepository, "update"),
    (RedemptionRepository, "create"),
    (PointLedgerRepository, "create"),
])
def test_redemption_rolls_back_every_flushed_step(
    client, auth_headers, db, funded_redemption, monkeypatch, repository, method_name,
):
    case = funded_redemption
    original = getattr(repository, method_name)

    def fail_after_write(self, *args, **kwargs):
        original(self, *args, **kwargs)
        raise RuntimeError("injected failure after write")

    with monkeypatch.context() as patch:
        patch.setattr(repository, method_name, fail_after_write)
        with pytest.raises(RuntimeError, match="injected failure after write"):
            client.post(case["path"], headers=auth_headers)

    assert not db.in_transaction()
    assert _persisted_state(db.get_bind(), case["user_id"], case["reward_id"]) == case["before"]
    response = client.post(case["path"], headers=auth_headers)
    assert response.status_code == 200
    after = _persisted_state(db.get_bind(), case["user_id"], case["reward_id"])
    assert after["balance"] == case["before"]["balance"] - 30
    assert after["reward_status"] == "redeemed"
    assert len(after["redemptions"]) == 1
    assert len(after["ledgers"]) == len(case["before"]["ledgers"]) + 1


def test_redemption_rolls_back_when_commit_fails(
    client, auth_headers, db, funded_redemption, monkeypatch,
):
    case = funded_redemption

    def fail_commit():
        assert db.get(User, case["user_id"]).current_value == case["before"]["balance"] - 30
        assert db.get(Reward, case["reward_id"]).status == "redeemed"
        assert db.query(Redemption).filter(Redemption.reward_id == case["reward_id"]).count() == 1
        ledger_count = db.query(PointLedger).filter(PointLedger.user_id == case["user_id"]).count()
        assert ledger_count == len(case["before"]["ledgers"]) + 1
        raise RuntimeError("injected commit failure")

    with monkeypatch.context() as patch:
        patch.setattr(db, "commit", fail_commit)
        with pytest.raises(RuntimeError, match="injected commit failure"):
            client.post(case["path"], headers=auth_headers)

    assert not db.in_transaction()
    assert _persisted_state(db.get_bind(), case["user_id"], case["reward_id"]) == case["before"]
    assert client.post(case["path"], headers=auth_headers).status_code == 200


def test_redemption_database_error_is_rolled_back_and_session_can_be_reused(
    client, auth_headers, db, funded_redemption, monkeypatch,
):
    case = funded_redemption
    original_create = PointLedgerRepository.create

    def fail_ledger_constraint(self, point_ledger):
        point_ledger.delta = None
        return original_create(self, point_ledger)

    with monkeypatch.context() as patch:
        patch.setattr(PointLedgerRepository, "create", fail_ledger_constraint)
        with pytest.raises(IntegrityError):
            client.post(case["path"], headers=auth_headers)

    assert db.is_active
    assert not db.in_transaction()
    assert _persisted_state(db.get_bind(), case["user_id"], case["reward_id"]) == case["before"]
    assert client.post(case["path"], headers=auth_headers).status_code == 200
