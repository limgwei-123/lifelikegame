from app.scoring_schemes.models import ScoringScheme
from datetime import datetime, timezone

from sqlalchemy.orm import Session

class ScoringSchemeRepository:
  def __init__(self, db:Session):
    self.db = db

  def create(self, scoring_scheme: ScoringScheme):
    self.db.add(scoring_scheme)
    self.db.flush()
    self.db.refresh(scoring_scheme)
    return scoring_scheme

  def list_by_user_id(self, user_id):
    return self._query().filter(ScoringScheme.user_id == user_id).all()

  def _query(self):
    return self.db.query(ScoringScheme).filter(ScoringScheme.deleted_at.is_(None))

  def get_by_id(self, scoring_scheme_id: int):
    return self._query().filter(
      ScoringScheme.id == scoring_scheme_id
    ).first()

  def get_by_id_and_user_id(self, scoring_scheme_id: int, user_id):
    return self._query().filter(
      ScoringScheme.user_id == user_id, ScoringScheme.id == scoring_scheme_id
    ).first()

  def update(self, scoring_scheme: ScoringScheme):
    self.db.flush()
    self.db.refresh(scoring_scheme)
    return scoring_scheme

  def delete(self, scoring_scheme: ScoringScheme):
    scoring_scheme.deleted_at = datetime.now(timezone.utc)
    self.db.flush()
