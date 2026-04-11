from pydantic import BaseModel, ConfigDict
from datetime import date,datetime
import uuid
from typing import Any, List
from app.task_schedules.models import ScheduleType


days={
  0: "Monday",
  1: "Tuesday",
  2: "Wednesday",
  3: "Thursday",
  4: "Friday",
  5: "Saturday",
  6: "Sunday"
}
class WeeklyValue(BaseModel):
    days: List[int]

class MonthlyValue(BaseModel):
    day: int


class CreateTaskScheduleRequest(BaseModel):
  schedule_type: ScheduleType
  schedule_value_json: dict[str, Any]
  start_date: date | None = None
  end_date: date | None = None

class UpdateTaskScheduleRequest(BaseModel):
  schedule_type: ScheduleType
  schedule_value_json: dict[str, Any]
  start_date: date | None = None
  end_date: date | None = None

class TaskScheduleResponse(BaseModel):
  id: int
  task_id: int
  user_id: uuid.UUID
  schedule_type: ScheduleType
  schedule_value_json: dict[str, Any]
  start_date: date | None
  end_date: date | None
  created_at: datetime
  updated_at: datetime

  model_config = ConfigDict(from_attributes=True)