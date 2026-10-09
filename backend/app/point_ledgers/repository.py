from app.point_ledgers.models import PointLedger
from app.users.models import User
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session
import uuid

class PointLedgerRepository:
  def __init__(self, db:Session):
    self.db = db

  def create(self, point_ledger: PointLedger):

    self.db.add(point_ledger)
    self.db.flush()
    self.db.refresh(point_ledger)
    return point_ledger

  def list_by_user_id(self, user_id):
    return self._query().filter(PointLedger.user_id == user_id).all()

  def _query(self):
    return self.db.query(PointLedger).filter(PointLedger.deleted_at.is_(None))

  def get_by_id(self, point_ledger_id):
    return self._query().filter(PointLedger.id == point_ledger_id).first()

  def get_by_id_and_user_id(self, point_ledger_id, user_id):
    return self._query().filter(PointLedger.id == point_ledger_id, PointLedger.user_id == user_id).first()

  def get_balance_by_user_id(self, user_id):
    balance = (
      self.db.query(func.coalesce(func.sum(PointLedger.delta), 0)).filter(
        PointLedger.user_id == user_id, PointLedger.deleted_at.is_(None),
      ).scalar()
    )
    return int(balance or 0)

  def get_balance_snapshot_by_user_id(self, user_id: uuid.UUID) -> tuple[int | None, int] | None:
    # One statement observes the cache and ledger at the same database snapshot.
    row = self.db.execute(
      select(User.current_value, func.coalesce(func.sum(PointLedger.delta), 0))
      .outerjoin(PointLedger, and_(
        PointLedger.user_id == User.id, PointLedger.deleted_at.is_(None),
      ))
      .where(User.id == user_id, User.deleted_at.is_(None))
      .group_by(User.id, User.current_value)
    ).one_or_none()
    return None if row is None else (row[0], int(row[1]))
