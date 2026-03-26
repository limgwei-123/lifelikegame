from pydantic import BaseModel, ConfigDict
from datetime import datetime
import uuid

class CreateScoringSchemeRequest(BaseModel):
    title: str = "normal"
    levels_json: dict[str, int]

class UpdateScoringSchemeRequest(BaseModel):
    title: str | None = None
    levels_json: dict[str, int] | None = None

class ScoringSchemeResponse(BaseModel):
    id: int
    user_id: uuid.UUID
    title: str
    levels_json: dict[str, int]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)