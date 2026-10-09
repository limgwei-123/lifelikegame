from dataclasses import dataclass
from datetime import date

from app.point_ledgers.models import PointLedger
from app.task_instances.models import TaskInstance
from app.users.models import User


@dataclass(frozen=True, slots=True)
class CompleteTaskInstanceResultDTO:
  task_instance: TaskInstance
  user: User
  point_ledger: PointLedger | None


@dataclass(frozen=True, slots=True)
class GenerateTaskInstancesResultDTO:
  target_date: date
  task_instances: tuple[TaskInstance, ...]
  processed_count: int
  created_count: int
