from app.point_ledgers.models import PointLedger
from sqlalchemy import func
from sqlalchemy.orm import Session

class PointLedgerRepository:
  def __init__(self, db:Session):
    self.db = db

  def create(self, point_ledger: PointLedger):

    self.db.add(point_ledger)
    self.db.commit()
    self.db.refresh(point_ledger)
    return point_ledger

  def list_by_user_id(self, user_id):
    return self.db.query(PointLedger).filter(PointLedger.user_id == user_id).all()

  def get_by_id_and_user_id(self, point_ledger_id, user_id):
    return self.db.query(PointLedger).filter(PointLedger.id == point_ledger_id, PointLedger.user_id == user_id).first()

  def get_balance_by_user_id(self, user_id):
    balance = (
      self.db.query(func.coalesce(func.sum(PointLedger.delta), 0)).filter(PointLedger.user_id == user_id).scalar()
    )
    return int(balance or 0)