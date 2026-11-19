from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime, date
import uuid
from app.shared.enums import RewardStatus

class CreateRewardRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    cost_points: int = Field(strict=True, ge=0)

class UpdateRewardRequest(BaseModel):
  title: str | None = None
  description: str | None = None
  cost_points: int | None = Field(default=None, strict=True, ge=0)
  status: RewardStatus | None = None

  @field_validator("cost_points", "status")
  @classmethod
  def reject_explicit_null(cls, value):
    if value is None:
      raise ValueError("Value must not be null")
    return value

class RewardResponse(BaseModel):
  id: int
  user_id: uuid.UUID
  title: str
  description: str | None = None
  cost_points: int | None = None
  status: str | None = None
  created_at: datetime
  updated_at: datetime

  model_config = ConfigDict(from_attributes=True)
