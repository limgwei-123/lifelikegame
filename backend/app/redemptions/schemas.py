from pydantic import BaseModel, ConfigDict
from datetime import datetime
import uuid

class CreateRedemptionRequest(BaseModel):
    reward_id: int


class RewardSnapshotSchema(BaseModel):
    title: str
    description: str | None = None
    cost_points: int

class RedemptionResponse(BaseModel):
  id: int
  user_id: uuid.UUID
  reward_id: int
  cost_points: int
  reward_snapshot_json: RewardSnapshotSchema | None = None
  created_at: datetime

  model_config = ConfigDict(from_attributes=True)
