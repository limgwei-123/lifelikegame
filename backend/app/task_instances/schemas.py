from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
import uuid
from typing import Any
from app.users.schemas import UserMeResponse
from app.point_ledgers.schemas import PointLedgerResponse

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import TaskInstanceStatus


class CreateTaskInstanceRequest(BaseModel):
    date_instance: date
class TaskInstanceResponse(BaseModel):
    id: int
    user_id: uuid.UUID
    task_id: int
    task_schedule_id: int | None
    date_instance: date
    status: TaskInstanceStatus
    completion_level: str | None
    score_awarded: int
    scoring_snapshot_json: dict[str, Any] | None = None
    generated_reason: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

class CompleteTaskInstanceResponse(BaseModel):
    task_instance: TaskInstanceResponse
    user: UserMeResponse
    point_ledger: PointLedgerResponse
class CompleteTaskInstanceRequest(BaseModel):
    completion_level: str = Field(min_length=1, max_length=100)