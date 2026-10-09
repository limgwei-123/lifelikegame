from app.point_ledgers.models import PointLedger
from app.point_ledgers.repository import PointLedgerRepository
from app.point_ledgers.schemas import CreatePointLedgerRequest
from app.point_ledgers.dtos import PointsReconciliationDTO
from app.users.interfaces import UserServiceInterface
from app.errors.exception import NotFoundError

from datetime import date

class PointLedgerService:
  def __init__(self, point_ledger_repo: PointLedgerRepository, user_service: UserServiceInterface):
    self.point_ledger_repo = point_ledger_repo
    self.user_service = user_service

  def create_point_ledger(self, user_id, payload: CreatePointLedgerRequest):

    user = self.user_service.get_user_by_id_for_update(user_id=user_id)
    if not user:
      raise NotFoundError("User not found")

    point_ledger = PointLedger(
       delta=payload.delta,
       entry_type=payload.entry_type,
       source_type=payload.source_type,
       source_id=payload.source_id,
       description=payload.description,
       user_id=user_id,
       event_at=date.today()
    )

    # The caller's UoW commits both writes together; workflows must not add delta again.
    created = self.point_ledger_repo.create(point_ledger)
    self.user_service.update_user_point(user_id=user_id, delta=payload.delta)
    return created

  def list_point_ledgers_by_user_id(self, user_id):
    return self.point_ledger_repo.list_by_user_id(user_id=user_id)

  def get_user_balance(self, user_id):
    return self.point_ledger_repo.get_balance_by_user_id(user_id=user_id)

  def get_balance_reconciliation(self, user_id) -> PointsReconciliationDTO:
    snapshot = self.point_ledger_repo.get_balance_snapshot_by_user_id(user_id=user_id)
    if snapshot is None:
      raise NotFoundError("User not found")
    return PointsReconciliationDTO(cached_balance=snapshot[0], ledger_balance=snapshot[1])
