"""Short-window protection for one API process; daily AI quota stays in DB."""

from math import ceil
from threading import Lock
import time
from typing import Callable

from fastapi import Depends, Request
from limits import RateLimitItem, RateLimitItemPerHour, RateLimitItemPerMinute
from limits.storage import MemoryStorage
from limits.strategies import FixedWindowRateLimiter

from app.auth.dependencies import get_current_user
from app.core.config import get_settings
from app.errors.exception import AppError
from app.users.models import User


class RequestRateLimitedError(AppError):
    code = "REQUEST_RATE_LIMITED"
    default_message = "Too many requests. Please try again later."
    status_code = 429

    def __init__(self, retry_after: int):
        self.retry_after = max(1, retry_after)
        super().__init__(details={"retry_after": self.retry_after})


class RequestRateLimiter:
    """Expire counters and refuse new identities at capacity, retaining live ones."""

    def __init__(self, *, max_keys: int = 1024, clock: Callable[[], float] = time.time):
        self._storage = MemoryStorage()
        self._limiter = FixedWindowRateLimiter(self._storage)
        self._expires: dict[str, float] = {}
        self._lock = Lock()
        self._max_keys = max_keys
        self._clock = clock

    def check(self, scope: str, subject: str, rule: RateLimitItem) -> None:
        key = rule.key_for(scope, subject)
        # Serialize admission across FastAPI worker threads, including capacity.
        with self._lock:
            now = self._clock()
            for expired in [key for key, reset in self._expires.items() if reset <= now]:
                self._storage.clear(expired)
                del self._expires[expired]
            if key not in self._expires and len(self._expires) >= self._max_keys:
                raise RequestRateLimitedError(ceil(min(self._expires.values()) - now))
            allowed = self._limiter.hit(rule, scope, subject)
            reset = self._limiter.get_window_stats(rule, scope, subject).reset_time
            self._expires[key] = reset
            if not allowed:
                raise RequestRateLimitedError(ceil(reset - now))

    def clear(self) -> None:
        with self._lock:
            self._storage.reset()
            self._expires.clear()


def get_request_limiter(request: Request) -> RequestRateLimiter:
    return request.app.state.request_limiter


def limit_login(request: Request, limiter: RequestRateLimiter = Depends(get_request_limiter)) -> None:
    # ASGI client comes from the socket or trusted server proxy configuration.
    # Never parse arbitrary X-Forwarded-For/Forwarded headers here.
    host = request.client.host if request.client else "unknown"
    limiter.check("login", host, RateLimitItemPerMinute(get_settings().login_requests_per_minute))


def limit_signup(request: Request, limiter: RequestRateLimiter = Depends(get_request_limiter)) -> None:
    host = request.client.host if request.client else "unknown"
    limiter.check("signup", host, RateLimitItemPerHour(get_settings().signup_requests_per_hour))


def require_ai_request(
    current_user: User = Depends(get_current_user),
    limiter: RequestRateLimiter = Depends(get_request_limiter),
) -> User:
    limiter.check("ai-generate", str(current_user.id), RateLimitItemPerMinute(get_settings().ai_requests_per_minute))
    return current_user
