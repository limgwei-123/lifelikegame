from app.db import get_db
from fastapi import Depends
from sqlalchemy.orm import Session

from app.scoring_schemes.interfaces import ScoringSchemeServiceInterface
from app.scoring_schemes.repository import ScoringSchemeRepository
from app.scoring_schemes.service import ScoringSchemeService

def build_scoring_scheme_service(db: Session)->ScoringSchemeServiceInterface:
  return ScoringSchemeService(
    scoring_scheme_repo=ScoringSchemeRepository(db)
  )

def get_scoring_scheme_service(
    db: Session = Depends(get_db)
)->ScoringSchemeServiceInterface:
  return build_scoring_scheme_service(db)