"""Player-local business dates, independent from the server's local timezone."""
from datetime import datetime, timezone, date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import get_settings
from app.errors.exception import RequestValidationError


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def player_zone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or get_settings().timezone)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise RequestValidationError([{
            'field': 'timezone', 'message': 'User timezone must be a valid IANA timezone',
            'code': 'invalid_timezone',
        }]) from error


def player_today(name: str | None, *, now: datetime | None = None) -> date:
    instant = now if now is not None else utc_now()
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError('Player date clock must be timezone-aware')
    return instant.astimezone(player_zone(name)).date()
