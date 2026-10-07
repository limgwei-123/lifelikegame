from dataclasses import dataclass
import uuid

from app.core.cqrs import TransactionalCommand
from app.workflows.task_workflow.dtos import CreateTaskWithScheduleDTO


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateTaskWithScheduleCommand(TransactionalCommand):
  goal_id: int
  user_id: uuid.UUID
  payload: CreateTaskWithScheduleDTO
