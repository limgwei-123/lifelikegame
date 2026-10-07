from dataclasses import dataclass
from datetime import date
import uuid

from app.core.cqrs import TransactionalCommand


@dataclass(frozen=True, slots=True, kw_only=True)
class CompleteTaskInstanceCommand(TransactionalCommand):
  task_instance_id: int
  user_id: uuid.UUID
  completion_level: str


@dataclass(frozen=True, slots=True, kw_only=True)
class GenerateDailyTaskInstancesCommand(TransactionalCommand):
  target_date: date
