from dataclasses import dataclass, fields
from datetime import datetime, timezone
from decimal import Decimal
import logging
from time import perf_counter
from typing import Callable


def safe_log(logger: logging.Logger, level: str, event: str, **values: object) -> None:
    try:
        getattr(logger, level)(event, extra=values)
    except Exception:
        pass


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cached_input_tokens: int | None = None
    thinking_tokens: int | None = None
    tool_input_tokens: int | None = None

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if type(value) is not int or not 0 <= value <= 2**63 - 1:
                object.__setattr__(self, field.name, None)


@dataclass(frozen=True)
class CallSnapshot:
    started_at: datetime
    finished_at: datetime
    latency_ms: Decimal
    attempts: int | None
    retry_count: int | None
    tokens: TokenUsage
    usage_scope: str = "reported_response"


class CallObservation:
    def __init__(self, *, clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
                 timer: Callable[[], float] = perf_counter):
        self.clock = clock
        self.timer = timer
        self._started_at: datetime | None = None
        self._started_timer: float | None = None
        self._attempts = 0
        self._attempts_known = True
        self._tokens = TokenUsage()
        self._snapshot: CallSnapshot | None = None

    def begin_dispatch(self) -> None:
        if self._started_at is None:
            self._started_at = self.clock().astimezone(timezone.utc)
            self._started_timer = self.timer()

    def attempt(self) -> None:
        self._attempts += 1

    def capture_usage(self, tokens: TokenUsage) -> None:
        self._tokens = tokens

    def finish(self) -> None:
        if self._started_at is None or self._snapshot is not None:
            return
        elapsed = Decimal(str(max(0.0, self.timer() - self._started_timer))) * 1000
        attempts = self._attempts if self._attempts_known and self._attempts > 0 else None
        self._snapshot = CallSnapshot(
            started_at=self._started_at, finished_at=self.clock().astimezone(timezone.utc),
            latency_ms=elapsed.quantize(Decimal("0.001")), attempts=attempts,
            retry_count=attempts - 1 if attempts is not None else None, tokens=self._tokens,
        )

    def snapshot(self) -> CallSnapshot | None:
        return self._snapshot


def safe_observe(observer: CallObservation | None, method: str, *args: object) -> None:
    if observer is None:
        return
    try:
        getattr(observer, method)(*args)
    except Exception:
        if method == "attempt":
            try:
                observer._attempts_known = False
            except Exception:
                pass
        safe_log(logging.getLogger("app.ai_usage"), "warning", "ai_observation_failed")
