"""Fixed calendar recurrence, with inclusive schedule bounds."""
from calendar import monthrange
from datetime import date, timedelta

from app.shared.enums import ScheduleType

MANAGED_RECURRENCE = 'recurring'


def tomorrow(value: date) -> date | None:
    return None if value == date.max else value + timedelta(days=1)


def next_on_or_after(schedule, earliest: date) -> date | None:
    candidate = max(earliest, schedule.start_date or earliest)
    kind = schedule.schedule_type
    if kind == ScheduleType.WEEKLY:
        days = [day for day in schedule.schedule_value_json.get('days', [])
                if type(day) is int and 0 <= day <= 6]
        if not days:
            return None
        offset = min((day - candidate.weekday()) % 7 for day in days)
        if (date.max - candidate).days < offset:
            return None
        candidate += timedelta(days=offset)
    elif kind == ScheduleType.MONTHLY:
        day = schedule.schedule_value_json.get('day')
        if type(day) is not int or not 1 <= day <= 31:
            return None
        year, month = candidate.year, candidate.month
        while True:
            if day <= monthrange(year, month)[1]:
                occurrence = date(year, month, day)
                if occurrence >= candidate:
                    candidate = occurrence
                    break
            if year == 9999 and month == 12:
                return None
            year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    elif kind != ScheduleType.DAILY:
        return None
    return None if schedule.end_date and candidate > schedule.end_date else candidate
