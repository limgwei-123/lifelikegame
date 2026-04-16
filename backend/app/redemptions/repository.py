from app.redemptions.models import Redemption
from sqlalchemy.orm import Session

class RedemptionRepository:
  def __init__(self, db: Session):
    self.db = db

  def create(self, redemption: Redemption):
    self.db.add(redemption)
    self.db.commit()
    self.db.refresh(redemption)
    return redemption

  def list_by_user_id(self, user_id):
    return self.db.query(Redemption).filter(Redemption.user_id == user_id).all()

  def get_by_id_and_user_id(self, redemption_id, user_id):
    return self.db.query(Redemption).filter(Redemption.id == redemption_id, Redemption.user_id == user_id).first()