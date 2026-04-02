from pydantic import BaseModel, ConfigDict
from datetime import datetime, date
import uuid

class CreateRewardRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    cost_points: int

class UpdateRewardRequest(BaseModel):
  title: str | None = None
  description: str | None = None
  cost_points: int | None = None

class RewardResponse(BaseModel):
  id: int
  user_id: uuid.UUID
  title: str
  description: str | None = None
  cost_points: int | None = None
  created_at: datetime
  updated_at: datetime

  model_config = ConfigDict(from_attributes=True)