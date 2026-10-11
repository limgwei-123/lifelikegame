from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Event
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select, text
from sqlalchemy.engine import Connection

from app.ai_planner.errors import (
    AIAdmissionUnavailableError, AIQuotaExceededError, AIRequestInProgressError,
)
from app.ai_planner.usage_models import AIDailyUsage
from app.ai_planner.usage_service import AIUsageAdmission, AIUsagePolicy
from ai_usage_support import ai_user_ids


NOW = datetime(2026, 10, 11, 12, tzinfo=timezone.utc)


def admission(db, limit=10, clock=lambda: NOW):
    return AIUsageAdmission(db.get_bind(), AIUsagePolicy(limit, ZoneInfo("Asia/Kuala_Lumpur")), clock)


def test_same_user_blocked_across_connections_other_user_independent(db, ai_user_ids):
    gate = admission(db)
    entered, release = Event(), Event()

    def worker():
        with gate.admit(ai_user_ids[0]) as charge:
            charge()
            entered.set()
            assert release.wait(10)

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(worker)
        try:
            assert entered.wait(10)
            with pytest.raises(AIRequestInProgressError):
                with gate.admit(ai_user_ids[0]):
                    pytest.fail("Concurrent request admitted")
            with gate.admit(ai_user_ids[1]) as charge:
                charge()
        finally:
            release.set()
        future.result(timeout=10)
    with gate.admit(ai_user_ids[0]) as charge:
        charge()


def test_charge_once_and_committed_even_if_provider_fails(db, ai_user_ids):
    gate = admission(db, limit=1)
    with pytest.raises(RuntimeError, match="provider"):
        with gate.admit(ai_user_ids[0]) as charge:
            charge()
            charge()
            raise RuntimeError("provider")
    assert db.scalar(select(AIDailyUsage.request_count).where(AIDailyUsage.user_id == ai_user_ids[0])) == 1
    with pytest.raises(AIQuotaExceededError) as error:
        with gate.admit(ai_user_ids[0]) as charge:
            charge()
    assert error.value.details == {"reset_at": "2026-10-11T16:00:00+00:00"}


def test_no_dispatch_no_charge_and_lock_released_on_error(db, ai_user_ids):
    gate = admission(db)
    with pytest.raises(ValueError):
        with gate.admit(ai_user_ids[0]):
            raise ValueError("local validation")
    assert db.scalar(select(AIDailyUsage).where(AIDailyUsage.user_id == ai_user_ids[0])) is None
    with gate.admit(ai_user_ids[0]) as charge:
        charge()


def test_midnight_uses_dispatch_day_but_does_not_change_lock(db, ai_user_ids):
    now = [datetime(2026, 10, 11, 15, 59, tzinfo=timezone.utc)]
    gate = admission(db, clock=lambda: now[0])
    with gate.admit(ai_user_ids[0]) as charge:
        now[0] = datetime(2026, 10, 11, 16, 1, tzinfo=timezone.utc)
        with pytest.raises(AIRequestInProgressError):
            with gate.admit(ai_user_ids[0]):
                pytest.fail("Midnight bypassed request lock")
        charge()
    row = db.scalar(select(AIDailyUsage).where(AIDailyUsage.user_id == ai_user_ids[0]))
    assert row.usage_date.isoformat() == "2026-10-12"


def test_guard_has_no_transaction_during_provider_wait(db, ai_user_ids, monkeypatch):
    transactions = []
    original = Connection.scalar

    def execute(connection, statement, *args, **kwargs):
        result = original(connection, statement, *args, **kwargs)
        if "pg_try_advisory_lock" in str(statement):
            transactions.append(connection)
        return result

    monkeypatch.setattr(Connection, "scalar", execute)
    with admission(db).admit(ai_user_ids[0]) as charge:
        assert not transactions[0].in_transaction()
        charge()
        assert not transactions[0].in_transaction()


@pytest.mark.parametrize("original_error", [False, True])
@pytest.mark.parametrize("failure_mode", ["false", "exception"])
def test_failed_unlock_invalidates_connection_and_preserves_provider_error(db, ai_user_ids, monkeypatch, original_error, failure_mode):
    original_execute, original_invalidate = Connection.scalar, Connection.invalidate
    invalidated = []

    def execute(connection, statement, *args, **kwargs):
        if "pg_advisory_unlock" in str(statement):
            if failure_mode == "exception":
                from sqlalchemy.exc import OperationalError
                raise OperationalError("private unlock SQL", {}, Exception("connection lost"))
            return original_execute(connection, text("SELECT false"))
        return original_execute(connection, statement, *args, **kwargs)

    def invalidate(connection, *args, **kwargs):
        invalidated.append(True)
        return original_invalidate(connection, *args, **kwargs)

    monkeypatch.setattr(Connection, "scalar", execute)
    monkeypatch.setattr(Connection, "invalidate", invalidate)
    expected = RuntimeError if original_error else AIAdmissionUnavailableError
    with pytest.raises(expected):
        with admission(db).admit(ai_user_ids[0]):
            if original_error:
                raise RuntimeError("provider")
    assert invalidated
    monkeypatch.setattr(Connection, "scalar", original_execute)
    with admission(db).admit(ai_user_ids[0]):
        pass


def test_counter_database_failure_fails_closed(db, ai_user_ids, monkeypatch):
    from sqlalchemy.exc import OperationalError
    from app.ai_planner.usage_repository import AIUsageRepository

    def fail(*args, **kwargs):
        raise OperationalError("private SQL", {}, Exception("private credentials"))

    monkeypatch.setattr(AIUsageRepository, "try_consume", fail)
    with pytest.raises(AIAdmissionUnavailableError) as error:
        with admission(db).admit(ai_user_ids[0]) as charge:
            charge()
    assert "private" not in str(error.value)
    with admission(db).admit(ai_user_ids[0]):
        pass


def test_database_connection_failure_is_safe_unavailable(db, ai_user_ids, monkeypatch):
    from sqlalchemy.exc import TimeoutError

    gate = admission(db)

    def unavailable():
        raise TimeoutError("private database connection details")

    monkeypatch.setattr(gate.engine, "connect", unavailable)
    with pytest.raises(AIAdmissionUnavailableError) as error:
        with gate.admit(ai_user_ids[0]):
            pytest.fail("Must fail closed")
    assert "private" not in str(error.value)
