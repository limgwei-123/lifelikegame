from pydantic import BaseModel, ConfigDict
from datetime import datetime
import uuid

class CreateTaskRequest(BaseModel):
  title: str
  description: str | None = None
  is_active: bool = True
  scoring_scheme_id: int | None = None
  scoring_scheme_json: dict | None = None
  is_scoring_scheme_locked: bool = False

class UpdateTaskRequest(BaseModel):
  title: str | None  = None
  description: str | None  = None
  is_active: bool = True
  scoring_scheme_id: str | None = None
  scoring_scheme_json: dict | None = None
  is_scoring_scheme_locked: bool = False
class TaskResponse(BaseModel):
  id: int
  goal_id: int
  user_id: uuid.UUID
  title: str
  description: str | None
  is_active: bool = True
  scoring_scheme_id: int | None = None
  scoring_scheme_json: dict | None = None
  is_scoring_scheme_locked: bool = False
  created_at: datetime
  updated_at: datetime

  model_config = ConfigDict(from_attributes=True)