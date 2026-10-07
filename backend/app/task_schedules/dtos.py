from dataclasses import dataclass
from datetime import date
from typing import Any

from app.shared.enums import ScheduleType


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateTaskScheduleDTO:
  schedule_type: ScheduleType
  schedule_value_json: dict[str, Any]
  start_date: date | None = None
  end_date: date | None = None
