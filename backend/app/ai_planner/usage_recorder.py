from dataclasses import asdict
import logging
import re
from typing import Literal, Mapping
from uuid import UUID

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.ai_planner.observation import CallSnapshot, safe_log
from app.ai_planner.pricing import CostEstimate, TokenPriceProfile, estimate_cost
from app.ai_planner.usage_record_models import AIUsageRecord
from app.ai_planner.usage_record_repository import AIUsageRecordRepository
from app.core.unit_of_work import build_unit_of_work


class AIUsageRecorder:
    def __init__(self, engine: Engine, profiles: Mapping[tuple[str, str], TokenPriceProfile],
                 logger: logging.Logger | None = None):
        self.engine = engine
        self.profiles = profiles
        self.logger = logger or logging.getLogger("app.ai_usage")

    def record(self, *, record_id: UUID, request_id: str, user_id: UUID, provider: str, model: str,
               observation: CallSnapshot, outcome: Literal["success", "error"], error_code: str | None) -> None:
        try:
            identifiers = ((request_id, 128), (provider, 32), (model, 128))
            if error_code is not None:
                identifiers += ((error_code, 64),)
            if any(not isinstance(value, str) or not 1 <= len(value) <= limit
                   or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*", value) is None
                   for value, limit in identifiers):
                raise ValueError("Invalid telemetry identifier")
            if observation.started_at.utcoffset() is None or observation.finished_at.utcoffset() is None:
                raise ValueError("Telemetry timestamps must be aware")
            if not observation.latency_ms.is_finite() or not 0 <= observation.latency_ms < 10**15:
                raise ValueError("Unsupported telemetry duration")
            try:
                cost = estimate_cost(observation, self.profiles.get((provider, model)))
            except Exception:
                cost = CostEstimate()
                safe_log(self.logger, "warning", "ai_usage_cost_failed")
            values = dict(
                id=record_id, user_id=user_id, request_id=request_id, provider=provider, model=model,
                started_at=observation.started_at, finished_at=observation.finished_at,
                latency_ms=observation.latency_ms, attempts=observation.attempts,
                retry_count=observation.retry_count, outcome=outcome, error_code=error_code,
                usage_scope=observation.usage_scope, **asdict(observation.tokens),
                estimated_cost=cost.amount, currency=cost.currency, price_version=cost.version, cost_status=cost.status,
            )
            # Own only a short telemetry transaction; the auth Session is never involved.
            try:
                with Session(self.engine) as session, build_unit_of_work(session).begin():
                    session.execute(text("SELECT set_config('lock_timeout', '1s', true)"))
                    session.execute(text("SELECT set_config('statement_timeout', '2s', true)"))
                    AIUsageRecordRepository(session).add(AIUsageRecord(**values))
            except Exception:
                safe_log(self.logger, "warning", "ai_usage_record_failed", record_id=str(record_id))
            summary = {key: value for key, value in values.items() if key not in ("id", "user_id", "started_at", "finished_at")}
            summary["record_id"] = str(record_id)
            summary["latency_ms"] = str(observation.latency_ms)
            summary["estimated_cost"] = str(cost.amount) if cost.amount is not None else None
            safe_log(self.logger, "info", "ai_usage_completed", **summary)
        except Exception:
            safe_log(self.logger, "warning", "ai_usage_record_failed")
