from app.redemptions.models import Redemption, REDEMPTION_REWARD_UNIQUE_CONSTRAINT
from app.errors.exception import ConflictError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

class RedemptionRepository:
  def __init__(self, db: Session):
    self.db = db

  def create(self, redemption: Redemption):
    self.db.add(redemption)
    try:
      self.db.flush()
    except IntegrityError as error:
      constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
      if constraint == REDEMPTION_REWARD_UNIQUE_CONSTRAINT:
        raise ConflictError("Reward has already been redeemed") from error
      raise
    self.db.refresh(redemption)
    return redemption

  def list_by_user_id(self, user_id):
    return self._query().filter(Redemption.user_id == user_id).all()

  def _query(self):
    return self.db.query(Redemption).filter(Redemption.deleted_at.is_(None))

  def get_by_id(self, redemption_id):
    return self._query().filter(Redemption.id == redemption_id).first()

  def get_by_id_and_user_id(self, redemption_id, user_id):
    return self._query().filter(Redemption.id == redemption_id, Redemption.user_id == user_id).first()
