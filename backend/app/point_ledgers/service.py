from app.point_ledgers.models import PointLedger
from app.point_ledgers.repository import PointLedgerRepository
from app.point_ledgers.schemas import CreatePointLedgerRequest

from datetime import date

class PointLedgerService:
  def __init__(self, point_ledger_repo: PointLedgerRepository):
    self.point_ledger_repo = point_ledger_repo

  def create_point_ledger(self, user_id, payload: CreatePointLedgerRequest):
    data = payload.model_dump()
    data['user_id'] = user_id
    data['event_at'] = date.today()
    return self.point_ledger_repo.create(data=data)

  def list_point_ledgers_by_user_id(self, user_id):
    return self.point_ledger_repo.list_by_user_id(user_id=user_id)

  def get_user_balance(self, user_id):
    return self.point_ledger_repo.get_balance_by_user_id(user_id=user_id)