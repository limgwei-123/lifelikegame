from typing import Protocol
import uuid
from app.point_ledgers.models import PointLedger
from app.point_ledgers.schemas import CreatePointLedgerRequest
from app.point_ledgers.dtos import PointsReconciliationDTO
class PointLedgerServiceInterface(Protocol):
    def create_point_ledger(self, user_id: uuid.UUID, payload: CreatePointLedgerRequest) -> PointLedger:
      ...

    def list_point_ledgers_by_user_id(self, user_id: uuid.UUID) -> list[PointLedger]:
      ...

    def get_user_balance(self, user_id: uuid.UUID) -> int:
      ...

    def get_balance_reconciliation(self, user_id: uuid.UUID) -> PointsReconciliationDTO:
      ...
