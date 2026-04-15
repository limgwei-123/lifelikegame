from pydantic import BaseModel, ConfigDict
from datetime import datetime,date
import uuid

class CreatePointLedgerRequest(BaseModel):
    delta: int
    entry_type: str
    source_type: str | None = None
    source_id: int | None = None
    description: str | None = None

class PointLedgerResponse(BaseModel):
    id: int
    user_id: uuid.UUID
    event_at: date
    delta: int
    entry_type: str
    source_type: str
    source_id: int | None
    description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PointsBalanceResponse(BaseModel):
    balance: int