import logging
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.auth.security import create_access_token
from app.errors.exception import NotFoundError, RequestValidationError
from app.point_ledgers.models import PointLedger
from app.redemptions.models import Redemption
from app.rewards.models import Reward
from app.users.models import User


@pytest.fixture
def command_redemption(db):
    user = User(email=f"redeem-command-{uuid4()}@example.com", password_hash="unused", current_value=100)
    db.add(user)
    db.flush()
    reward = Reward(user_id=user.id, title="Command reward", cost_points=60)
    db.add(reward)
    db.add(PointLedger(user_id=user.id, delta=100, entry_type="earn", source_type="test_funding"))
    db.commit()
    case = {"user_id": user.id, "reward_id": reward.id}
    db.rollback()
    case["headers"] = {"Authorization": f"Bearer {create_access_token(sub=str(case['user_id']))}"}
    return case


def _state(bind, case):
    with Session(bind) as reader:
        return (
            reader.get(User, case["user_id"]).current_value,
            reader.get(Reward, case["reward_id"]).status,
            reader.query(Redemption).filter(Redemption.reward_id == case["reward_id"]).count(),
            [row.delta for row in reader.query(PointLedger).filter(
                PointLedger.user_id == case["user_id"],
            ).order_by(PointLedger.id).all()],
        )


def test_redemption_api_uses_command_pipeline_and_commits_once(client, db, command_redemption, monkeypatch, caplog):
    case = command_redemption
    commits = []
    original_commit = db.commit

    def commit():
        commits.append(True)
        original_commit()

    monkeypatch.setattr(db, "commit", commit)
    with caplog.at_level(logging.INFO, logger="app.cqrs"):
        response = client.post(f"/workflows/rewards/{case['reward_id']}/redeem", headers=case["headers"])
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"redemption_id", "reward_id", "reward_title", "cost_points", "remaining_points", "redeemed_at"}
    assert data["reward_id"] == case["reward_id"]
    assert data["reward_title"] == "Command reward"
    assert data["cost_points"] == 60
    assert data["remaining_points"] == 40
    assert data["redeemed_at"]
    assert commits == [True]
    assert _state(db.get_bind(), case) == (40, "redeemed", 1, [100, -60])
    records = [record for record in caplog.records if getattr(record, "request_type", None) == "RedeemRewardCommand"]
    assert len(records) == 1
    assert records[0].handler_type == "RedeemRewardCommandHandler"
    assert records[0].transactional is True
    assert records[0].outcome == "success"
    assert records[0].request_id


@pytest.mark.parametrize("reward_id", [0, -1])
def test_redemption_api_rejects_invalid_reward_id_before_business_execution(client, db, command_redemption, reward_id):
    response = client.post(f"/workflows/rewards/{reward_id}/redeem", headers=command_redemption["headers"])
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["details"]["issues"][0]["field"] == "reward_id"
    assert _state(db.get_bind(), command_redemption) == (100, "available", 0, [100])


def test_command_commits_outside_http_and_returns_an_internal_result(db, command_redemption):
    from app.workflows.redemption_workflow.commands import RedeemRewardCommand
    from app.workflows.redemption_workflow.dependencies import build_redeem_reward_mediator
    from app.workflows.redemption_workflow.dtos import RedeemRewardResultDTO

    case = command_redemption
    result = build_redeem_reward_mediator(db).send(RedeemRewardCommand(
        reward_id=case["reward_id"], user_id=case["user_id"],
    ))
    assert isinstance(result, RedeemRewardResultDTO)
    assert result.remaining_points == 40
    assert result.cost_points == 60
    assert not db.in_transaction()
    assert _state(db.get_bind(), case) == (40, "redeemed", 1, [100, -60])


def test_handler_does_not_commit_independently(db, command_redemption):
    from app.workflows.redemption_workflow.commands import RedeemRewardCommand
    from app.workflows.redemption_workflow.dependencies import build_redemption_workflow_service
    from app.workflows.redemption_workflow.handlers import RedeemRewardCommandHandler

    case = command_redemption
    with Session(db.get_bind()) as session:
        result = RedeemRewardCommandHandler(build_redemption_workflow_service(session)).handle(
            RedeemRewardCommand(reward_id=case["reward_id"], user_id=case["user_id"]),
        )
        assert result.remaining_points == 40
        assert _state(db.get_bind(), case) == (100, "available", 0, [100])
        session.rollback()
    assert _state(db.get_bind(), case) == (100, "available", 0, [100])


@pytest.mark.parametrize("reward_id", [0, -1, True, "1", 1.5])
def test_non_http_command_validates_reward_id_before_writing(db, command_redemption, reward_id):
    from app.workflows.redemption_workflow.commands import RedeemRewardCommand
    from app.workflows.redemption_workflow.dependencies import build_redeem_reward_mediator

    with pytest.raises(RequestValidationError) as error:
        build_redeem_reward_mediator(db).send(RedeemRewardCommand(
            reward_id=reward_id, user_id=command_redemption["user_id"],
        ))
    assert error.value.details["issues"][0]["field"] == "reward_id"
    assert not db.in_transaction()
    assert _state(db.get_bind(), command_redemption) == (100, "available", 0, [100])


@pytest.mark.parametrize("user_id", [None, "not-a-uuid"])
def test_non_http_command_rejects_invalid_user_id(db, command_redemption, user_id):
    from app.workflows.redemption_workflow.commands import RedeemRewardCommand
    from app.workflows.redemption_workflow.dependencies import build_redeem_reward_mediator

    with pytest.raises(RequestValidationError) as error:
        build_redeem_reward_mediator(db).send(RedeemRewardCommand(
            reward_id=command_redemption["reward_id"], user_id=user_id,
        ))
    assert error.value.details["issues"][0]["field"] == "user_id"
    assert _state(db.get_bind(), command_redemption) == (100, "available", 0, [100])


def test_non_http_command_cannot_redeem_another_users_reward(db, command_redemption):
    from app.workflows.redemption_workflow.commands import RedeemRewardCommand
    from app.workflows.redemption_workflow.dependencies import build_redeem_reward_mediator

    other = User(email=f"other-command-{uuid4()}@example.com", password_hash="unused", current_value=100)
    db.add(other)
    db.commit()
    command = RedeemRewardCommand(reward_id=command_redemption["reward_id"], user_id=other.id)
    db.rollback()
    with pytest.raises(NotFoundError):
        build_redeem_reward_mediator(db).send(command)
    assert not db.in_transaction()
    assert _state(db.get_bind(), command_redemption) == (100, "available", 0, [100])


def test_non_http_command_rolls_back_commit_failure_and_can_retry(db, command_redemption, monkeypatch, caplog):
    from app.workflows.redemption_workflow.commands import RedeemRewardCommand
    from app.workflows.redemption_workflow.dependencies import build_redeem_reward_mediator

    case = command_redemption
    mediator = build_redeem_reward_mediator(db)
    command = RedeemRewardCommand(reward_id=case["reward_id"], user_id=case["user_id"])

    def fail_commit():
        assert db.get(User, case["user_id"]).current_value == 40
        assert db.get(Reward, case["reward_id"]).status == "redeemed"
        assert db.query(Redemption).filter(Redemption.reward_id == case["reward_id"]).count() == 1
        assert db.query(PointLedger).filter(PointLedger.user_id == case["user_id"]).count() == 2
        raise RuntimeError("injected command commit failure")

    with monkeypatch.context() as patch, caplog.at_level(logging.INFO, logger="app.cqrs"):
        patch.setattr(db, "commit", fail_commit)
        with pytest.raises(RuntimeError, match="injected command commit failure"):
            mediator.send(command)
    assert not db.in_transaction()
    assert db.is_active
    assert _state(db.get_bind(), case) == (100, "available", 0, [100])
    assert any(getattr(record, "request_type", None) == "RedeemRewardCommand"
               and record.outcome == "failure" for record in caplog.records)
    assert mediator.send(command).remaining_points == 40
    assert _state(db.get_bind(), case) == (40, "redeemed", 1, [100, -60])


@pytest.mark.parametrize("entrypoint", ["api", "command"])
def test_invalid_persisted_result_data_cannot_commit_redemption(client, db, command_redemption, entrypoint):
    from app.workflows.redemption_workflow.commands import RedeemRewardCommand
    from app.workflows.redemption_workflow.dependencies import build_redeem_reward_mediator

    case = command_redemption
    db.get(Reward, case["reward_id"]).title = None
    db.commit()
    with pytest.raises(ValueError):
        if entrypoint == "api":
            client.post(f"/workflows/rewards/{case['reward_id']}/redeem", headers=case["headers"])
        else:
            build_redeem_reward_mediator(db).send(RedeemRewardCommand(
                reward_id=case["reward_id"], user_id=case["user_id"],
            ))
    assert _state(db.get_bind(), case) == (100, "available", 0, [100])
    with Session(db.get_bind()) as reader:
        assert reader.get(Reward, case["reward_id"]).title is None
