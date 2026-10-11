from dataclasses import dataclass
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from hashlib import blake2b
from typing import Callable, Iterator
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai_planner.errors import (
    AIAdmissionUnavailableError, AIQuotaExceededError, AIRequestInProgressError,
)
from app.ai_planner.usage_repository import AIUsageRepository
from app.core.unit_of_work import build_unit_of_work
from app.ai_planner.interfaces import AIPlannerServiceInterface
from app.ai_planner.providers.base import AIPlannerProvider
from app.ai_planner.schemas import AiPlannerChatRequest, AiPlannerResponse
from app.ai_planner.service import AIPlannerService


@dataclass(frozen=True)
class AIUsagePolicy:
    limit: int
    timezone: ZoneInfo

    def __post_init__(self) -> None:
        if self.limit <= 0:
            raise ValueError("AI daily limit must be positive")

    def window(self, now: datetime) -> tuple[date, datetime]:
        if now.utcoffset() is None:
            raise ValueError("AI usage clock must be timezone-aware")
        day = now.astimezone(self.timezone).date()
        reset = datetime.combine(day + timedelta(days=1), time.min, tzinfo=self.timezone)
        return day, reset


def _usage_lock_key(user_id: UUID) -> int:
    digest = blake2b(b"lifelikegame:ai-usage:" + user_id.bytes, digest_size=8).digest()
    return int.from_bytes(digest, "big", signed=True)


class AIUsageAdmission:
    def __init__(self, engine: Engine, policy: AIUsagePolicy, clock: Callable[[], datetime]):
        self.engine = engine
        self.policy = policy
        self.clock = clock

    @contextmanager
    def admit(self, user_id: UUID) -> Iterator[Callable[[], None]]:
        try:
            connection = self.engine.connect()
        except SQLAlchemyError as exc:
            raise AIAdmissionUnavailableError() from exc
        key = _usage_lock_key(user_id)
        locked = False
        failed = False
        charged = False
        active = True
        try:
            try:
                locked = bool(connection.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": key}))
                connection.commit()
            except SQLAlchemyError as exc:
                connection.invalidate()
                locked = False
                raise AIAdmissionUnavailableError() from exc
            if not locked:
                raise AIRequestInProgressError()

            def before_send() -> None:
                nonlocal charged
                if not active:
                    raise RuntimeError("AI admission has already closed")
                if charged:
                    return
                day, reset = self.policy.window(self.clock())
                try:
                    # A separate short UoW must own this transaction, not the auth Session.
                    with Session(bind=connection) as session:
                        with build_unit_of_work(session).begin():
                            if not AIUsageRepository(session).try_consume(user_id, day, self.policy.limit):
                                raise AIQuotaExceededError(reset)
                except SQLAlchemyError as exc:
                    raise AIAdmissionUnavailableError() from exc
                charged = True

            yield before_send
        except BaseException:
            failed = True
            raise
        finally:
            active = False
            try:
                if connection.in_transaction():
                    connection.rollback()
                if locked:
                    unlocked = connection.scalar(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
                    if not unlocked:
                        raise RuntimeError("AI admission lock was not released")
                    connection.commit()
            except Exception as exc:
                # Rollback cannot release a session lock; never return it to the pool.
                connection.invalidate()
                if not failed:
                    raise AIAdmissionUnavailableError() from exc
            finally:
                connection.close()


class UsageLimitedAIPlannerService(AIPlannerServiceInterface):
    def __init__(self, user_id: UUID, admission: AIUsageAdmission, provider_factory: Callable[..., AIPlannerProvider]):
        self.user_id = user_id
        self.admission = admission
        self.provider_factory = provider_factory

    def generate_plan(self, payload: AiPlannerChatRequest) -> AiPlannerResponse:
        with self.admission.admit(self.user_id) as before_send:
            provider = self.provider_factory(before_send=before_send)
            return AIPlannerService(provider).generate_plan(payload)
