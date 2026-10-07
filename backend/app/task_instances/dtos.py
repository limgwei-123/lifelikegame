from dataclasses import dataclass

from app.point_ledgers.models import PointLedger
from app.task_instances.models import TaskInstance
from app.users.models import User


@dataclass(frozen=True, slots=True)
class CompleteTaskInstanceResultDTO:
  task_instance: TaskInstance
  user: User
  point_ledger: PointLedger | None
