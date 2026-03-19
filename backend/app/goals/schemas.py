from pydantic import BaseModel, ConfigDict
from datetime import date
from typing import Optional
import uuid

class CreateGoalRequest(BaseModel):
  title: str | None
  start_date: date | None = None
  target_date: Optional[date] = None
  current_value: Optional[str] = None
  target_value: Optional[str] = None

class UpdateGoalRequest(BaseModel):
  title: str
  start_date: date
  target_date: Optional[date] = None
  current_value: Optional[str] = None
  target_value: Optional[str] = None

class GoalResponse(BaseModel):
  id: int
  user_id: uuid.UUID
  title: str
  start_date: date
  target_date: Optional[date] = None
  current_value: Optional[str] = None
  target_value: Optional[str] = None

  model_config = ConfigDict(from_attributes=True)
