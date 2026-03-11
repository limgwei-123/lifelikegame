from pydantic import BaseModel, ConfigDict
from datetime import date
from typing import Optional
from app.auth.schemas import UserMeResponse
import uuid

class CreateGoalRequest(BaseModel):
  title: str
  start_date: date
  target_date: Optional[date] = None
  current_value: Optional[str] = None
  target_value: Optional[str] = None

class GoalResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: int
  user_id: uuid.UUID
  user: UserMeResponse
  title: str
  start_date: date
  target_date: Optional[date] = None
  current_value: Optional[str] = None
  target_value: Optional[str] = None