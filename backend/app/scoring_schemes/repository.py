from app.scoring_schemes.models import ScoringScheme

from sqlalchemy.orm import Session

class ScoringSchemeRepository:
  def __init__(self, db:Session):
    self.db = db

  def create(self, scoring_scheme: ScoringScheme):
    self.db.add(scoring_scheme)
    self.db.commit()
    self.db.refresh(scoring_scheme)
    return scoring_scheme

  def list_by_user_id(self, user_id):
    return self.db.query(ScoringScheme).filter(ScoringScheme.user_id == user_id).all()

  def get_by_id(self, scoring_scheme_id: int):
    return self.db.query(ScoringScheme).filter(
      ScoringScheme.id == scoring_scheme_id
    ).first()

  def get_by_id_and_user_id(self, scoring_scheme_id: int, user_id):
    return self.db.query(ScoringScheme).filter(
      ScoringScheme.user_id == user_id, ScoringScheme.id == scoring_scheme_id
    ).first()

  def update(self, scoring_scheme: ScoringScheme):
    self.db.commit()
    self.db.refresh(scoring_scheme)
    return scoring_scheme

  def delete(self, scoring_scheme: ScoringScheme):
    self.db.delete(scoring_scheme)
    self.db.commit()