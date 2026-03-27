from typing import Protocol

class PointLedgerServiceInterface(Protocol):
    def create_point_ledger(self, user_id, payload):
      ...

    def list_point_ledgers_by_user_id(self, user_id):
      ...

    def get_user_balance(self, user_id):
      ...