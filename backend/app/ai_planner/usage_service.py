from dataclasses import dataclass
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from hashlib import blake2b
import logging
import re
from typing import Callable, Iterator
from uuid import UUID, uuid4
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
from app.ai_planner.observation import CallObservation, safe_log
from app.ai_planner.usage_recorder import AIUsageRecorder
from app.core.behaviors import get_request_id
from app.errors.exception import AppError


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
    def __init__(self, user_id: UUID, admission: AIUsageAdmission, provider_factory: Callable[..., AIPlannerProvider],
                 *, recorder: AIUsageRecorder | None = None, provider_name: str | None = None, model_name: str | None = None):
        self.user_id = user_id
        self.admission = admission
        self.provider_factory = provider_factory
        self.recorder = recorder
        self.provider_name = provider_name
        self.model_name = model_name

    def generate_plan(self, payload: AiPlannerChatRequest) -> AiPlannerResponse:
        observation = None
        record_id, request_id = None, None
        if self.recorder is not None:
            try:
                record_id = uuid4()
                request_id = get_request_id()
                if not isinstance(request_id, str) or not 1 <= len(request_id) <= 128 or re.fullmatch(
                    r"[A-Za-z0-9][A-Za-z0-9._:/-]*", request_id,
                ) is None:
                    request_id = str(uuid4())
                observation = CallObservation()
            except Exception:
                safe_log(logging.getLogger("app.ai_usage"), "warning", "ai_observation_failed")
        outcome, error_code = "error", "AI_INTERNAL_ERROR"
        try:
            with self.admission.admit(self.user_id) as before_send:
                options = {"before_send": before_send}
                if observation is not None:
                    options["observation"] = observation
                provider = self.provider_factory(**options)
                result = AIPlannerService(provider).generate_plan(payload)
            outcome, error_code = "success", None
            return result
        except AppError as exc:
            error_code = exc.code
            raise
        finally:
            # The guard is released before any best-effort telemetry work begins.
            if observation is not None:
                try:
                    snapshot = observation.snapshot()
                    if snapshot is not None:
                        self.recorder.record(
                            record_id=record_id, request_id=request_id, user_id=self.user_id,
                            provider=self.provider_name, model=self.model_name, observation=snapshot,
                            outcome=outcome, error_code=error_code,
                        )
                except Exception:
                    safe_log(logging.getLogger("app.ai_usage"), "warning", "ai_usage_record_failed")
