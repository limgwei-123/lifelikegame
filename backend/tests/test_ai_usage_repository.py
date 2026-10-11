from datetime import date, datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from ai_usage_support import ai_user_ids
from app.ai_planner.usage_models import AIDailyUsage
from app.core.config import Settings
from app.core.unit_of_work import build_unit_of_work


def test_quota_is_persisted_and_separate_by_user_and_date(db, ai_user_ids):
    from app.ai_planner.usage_repository import AIUsageRepository

    engine = db.get_bind()
    user_id, other_id = ai_user_ids
    day = date(2026, 10, 11)
    for i in range(11):
        with Session(engine) as session, build_unit_of_work(session).begin():
            assert AIUsageRepository(session).try_consume(user_id, day, 10) is (i < 10)
    with Session(engine) as session, build_unit_of_work(session).begin():
        repo = AIUsageRepository(session)
        assert not repo.try_consume(user_id, day, 2)
        assert repo.try_consume(other_id, day, 10)
        assert repo.try_consume(user_id, date(2026, 10, 12), 10)
    with Session(engine) as reader:
        assert reader.get(AIDailyUsage, (user_id, day)).request_count == 10
        assert reader.get(AIDailyUsage, (other_id, day)).request_count == 1
        assert reader.get(AIDailyUsage, (user_id, date(2026, 10, 12))).request_count == 1


def test_repository_does_not_commit_its_own_work(db, ai_user_ids):
    from app.ai_planner.usage_repository import AIUsageRepository

    day = date(2026, 10, 11)
    assert AIUsageRepository(db).try_consume(ai_user_ids[0], day, 10)
    db.rollback()
    assert db.get(AIDailyUsage, (ai_user_ids[0], day)) is None


def test_atomic_counter_never_exceeds_limit_under_competing_connections(db, ai_user_ids):
    from app.ai_planner.usage_repository import AIUsageRepository

    barrier = Barrier(4)
    day = date(2026, 10, 11)
    engine = db.get_bind()

    def consume(_):
        with Session(engine) as session, build_unit_of_work(session).begin():
            barrier.wait(timeout=10)
            return AIUsageRepository(session).try_consume(ai_user_ids[0], day, 5)

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(consume, range(12))) == 5
    assert db.get(AIDailyUsage, (ai_user_ids[0], day)).request_count == 5


@pytest.mark.parametrize("zone,instant,want_day,want_reset", [
    ("Asia/Kuala_Lumpur", "2026-10-11T15:59:59+00:00", date(2026, 10, 11), "2026-10-11T16:00:00+00:00"),
    ("Asia/Kuala_Lumpur", "2026-10-11T16:00:00+00:00", date(2026, 10, 12), "2026-10-12T16:00:00+00:00"),
    ("America/New_York", "2026-03-08T06:00:00+00:00", date(2026, 3, 8), "2026-03-09T04:00:00+00:00"),
])
def test_calendar_uses_system_zone_and_next_local_midnight(zone, instant, want_day, want_reset):
    from app.ai_planner.usage_service import AIUsagePolicy

    day, reset = AIUsagePolicy(10, ZoneInfo(zone)).window(datetime.fromisoformat(instant))
    assert day == want_day
    assert reset.astimezone(timezone.utc).isoformat() == want_reset


def test_calendar_rejects_naive_clock():
    from app.ai_planner.usage_service import AIUsagePolicy

    with pytest.raises(ValueError):
        AIUsagePolicy(10, ZoneInfo("UTC")).window(datetime(2026, 10, 11))


@pytest.mark.parametrize("limit", [0, -1])
def test_daily_limit_must_be_positive(limit):
    with pytest.raises(ValidationError):
        Settings(ai_daily_request_limit=limit, _env_file=None)


def test_daily_limit_can_be_configured(monkeypatch):
    monkeypatch.delenv("AI_DAILY_REQUEST_LIMIT", raising=False)
    assert Settings(_env_file=None).ai_daily_request_limit == 10
    monkeypatch.setenv("AI_DAILY_REQUEST_LIMIT", "2")
    assert Settings(_env_file=None).ai_daily_request_limit == 2
