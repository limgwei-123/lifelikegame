import json
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError, OperationalError, TimeoutError
from sqlalchemy.orm import Session

from app.ai_planner.pricing import load_price_profiles
from app.ai_planner.usage_record_models import AIUsageRecord
from app.ai_planner.usage_record_repository import AIUsageRecordRepository
from app.ai_planner.usage_recorder import AIUsageRecorder
from app.users.models import User
from ai_usage_support import ai_user_ids
from test_ai_pricing import profile_data, sample_snapshot


def record_args(user_id):
    return dict(record_id=uuid4(), request_id=str(uuid4()), user_id=user_id,
                provider="gemini", model="test", observation=sample_snapshot(), outcome="success", error_code=None)


def test_recorder_persists_snapshot_and_immutable_price_version(db, ai_user_ids):
    profiles = load_price_profiles(json.dumps([profile_data()]))
    kwargs = record_args(ai_user_ids[0])
    AIUsageRecorder(db.get_bind(), profiles).record(**kwargs)
    row = db.get(AIUsageRecord, kwargs["record_id"])
    assert (row.attempts, row.retry_count, row.outcome) == (1, 0, "success")
    assert row.estimated_cost == Decimal("0.001200000000")
    assert row.price_version == "v1"
    assert row.prompt_tokens == 1000 and row.tool_input_tokens == 0
    data = profile_data()
    data["version"] = "v2"
    AIUsageRecorder(db.get_bind(), load_price_profiles(json.dumps([data]))).record(**record_args(ai_user_ids[0]))
    db.expire_all()
    assert db.get(AIUsageRecord, kwargs["record_id"]).price_version == "v1"


def test_record_id_is_unique_and_duplicate_does_not_replace(db, ai_user_ids):
    kwargs = record_args(ai_user_ids[0])
    recorder = AIUsageRecorder(db.get_bind(), {})
    recorder.record(**kwargs)
    kwargs["outcome"], kwargs["error_code"] = "error", "AI_TIMEOUT"
    recorder.record(**kwargs)
    assert db.get(AIUsageRecord, kwargs["record_id"]).outcome == "success"


def test_repository_does_not_commit_and_user_delete_cascades(db, ai_user_ids):
    kwargs = record_args(ai_user_ids[0])
    recorder = AIUsageRecorder(db.get_bind(), {})
    recorder.record(**kwargs)
    row = db.get(AIUsageRecord, kwargs["record_id"])
    db.delete(row)
    db.flush()
    db.rollback()
    assert db.get(AIUsageRecord, kwargs["record_id"]) is not None
    values = {column.name: getattr(row, column.name) for column in row.__table__.columns}
    values["id"] = uuid4()
    AIUsageRecordRepository(db).add(AIUsageRecord(**values))
    db.rollback()
    assert db.get(AIUsageRecord, values["id"]) is None
    db.delete(db.get(User, ai_user_ids[0]))
    db.commit()
    assert db.get(AIUsageRecord, kwargs["record_id"]) is None


@pytest.mark.parametrize("updates", [
    {"prompt_tokens": -1}, {"attempts": 0}, {"retry_count": 2},
    {"latency_ms": -1}, {"estimated_cost": -1}, {"outcome": "other"}, {"cost_status": "billed"},
])
def test_constraints_reject_invalid_record_values(db, ai_user_ids, updates):
    kwargs = record_args(ai_user_ids[0])
    AIUsageRecorder(db.get_bind(), {}).record(**kwargs)
    row = db.get(AIUsageRecord, kwargs["record_id"])
    values = {column.name: getattr(row, column.name) for column in row.__table__.columns}
    values.update(id=uuid4(), **updates)
    with pytest.raises(IntegrityError), db.begin_nested():
        AIUsageRecordRepository(db).add(AIUsageRecord(**values))


def test_recorder_preserves_unrelated_pending_auth_write(db, ai_user_ids):
    other = db.get(User, ai_user_ids[1])
    original = other.email
    other.email = f"pending-{uuid4()}@example.com"
    db.flush()
    kwargs = record_args(ai_user_ids[0])
    AIUsageRecorder(db.get_bind(), {}).record(**kwargs)
    with Session(db.get_bind()) as observer:
        assert observer.get(User, ai_user_ids[1]).email == original
        assert observer.get(AIUsageRecord, kwargs["record_id"]) is not None
    assert db.in_transaction() and other.email != original
    db.rollback()
    assert other.email == original


def test_recording_connection_insert_and_logger_failures_are_safe(db, ai_user_ids, monkeypatch, caplog):
    recorder = AIUsageRecorder(db.get_bind(), {})
    kwargs = record_args(ai_user_ids[0])

    def fail(*args, **kwargs):
        raise OperationalError("PRIVATE SQL", {}, Exception("PRIVATE credentials"))

    monkeypatch.setattr(AIUsageRecordRepository, "add", fail)
    recorder.record(**kwargs)
    assert db.get(AIUsageRecord, kwargs["record_id"]) is None
    assert "ai_usage_record_failed" in caplog.text
    assert "PRIVATE" not in caplog.text
    monkeypatch.setattr(recorder.logger, "info", fail)
    monkeypatch.setattr(recorder.logger, "warning", fail)
    recorder.record(**kwargs)
    monkeypatch.setattr(recorder.engine, "connect", lambda: (_ for _ in ()).throw(TimeoutError("PRIVATE pool")))
    recorder.record(**kwargs)


def test_cost_calculation_failure_preserves_known_usage(db, ai_user_ids, monkeypatch):
    from app.ai_planner import usage_recorder
    monkeypatch.setattr(usage_recorder, "estimate_cost", lambda *args: (_ for _ in ()).throw(ValueError("PRIVATE")))
    kwargs = record_args(ai_user_ids[0])
    AIUsageRecorder(db.get_bind(), {}).record(**kwargs)
    row = db.get(AIUsageRecord, kwargs["record_id"])
    assert row.prompt_tokens == 1000 and row.estimated_cost is None and row.cost_status == "unknown"


def test_local_timeouts_are_used_and_never_leak_to_pool(db, ai_user_ids, monkeypatch):
    engine = create_engine(db.get_bind().url, pool_size=1, max_overflow=0)
    original = AIUsageRecordRepository.add
    seen = []

    def inspect(repository, row):
        seen.append((repository.session.scalar(text("SHOW lock_timeout")),
                     repository.session.scalar(text("SHOW statement_timeout"))))
        return original(repository, row)

    monkeypatch.setattr(AIUsageRecordRepository, "add", inspect)
    try:
        with engine.connect() as connection:
            before = (connection.scalar(text("SHOW lock_timeout")), connection.scalar(text("SHOW statement_timeout")))
        AIUsageRecorder(engine, {}).record(**record_args(ai_user_ids[0]))
        assert seen == [("1s", "2s")]
        with engine.connect() as connection:
            after = (connection.scalar(text("SHOW lock_timeout")), connection.scalar(text("SHOW statement_timeout")))
        assert before == after
    finally:
        engine.dispose()


def test_fk_lock_timeout_keeps_callers_transaction_intact(db, ai_user_ids, caplog):
    db.execute(select(User).where(User.id == ai_user_ids[0]).with_for_update())
    kwargs = record_args(ai_user_ids[0])
    AIUsageRecorder(db.get_bind(), {}).record(**kwargs)
    assert db.in_transaction()
    assert db.get(AIUsageRecord, kwargs["record_id"]) is None
    assert "ai_usage_record_failed" in caplog.text
    db.rollback()
