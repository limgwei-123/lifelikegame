from typing import Protocol
from app.point_ledgers.schemas import CreatePointLedgerRequest
class PointLedgerServiceInterface(Protocol):
    def create_point_ledger(self, user_id, payload:CreatePointLedgerRequest):
      ...

    def list_point_ledgers_by_user_id(self, user_id):
      ...

    def get_user_balance(self, user_id):
      ...