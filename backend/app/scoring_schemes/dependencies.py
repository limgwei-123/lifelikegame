from app.db import get_db
from fastapi import Depends
from sqlalchemy.orm import Session

from app.scoring_schemes.interfaces import ScoringSchemeServiceInterface
from app.scoring_schemes.repository import ScoringSchemeRepository
from app.scoring_schemes.service import ScoringSchemeService

def get_scoring_scheme_repository(
    db: Session = Depends(get_db)
)->ScoringSchemeRepository:
  return ScoringSchemeRepository(db)

def get_scoring_scheme_service(
    scoring_scheme_repo: ScoringSchemeRepository = Depends(get_scoring_scheme_repository)
)->ScoringSchemeServiceInterface:
  return ScoringSchemeService(scoring_scheme_repo=scoring_scheme_repo)