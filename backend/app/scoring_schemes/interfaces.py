from typing import Protocol
import uuid
from app.scoring_schemes.models import ScoringScheme
from app.scoring_schemes.schemas import CreateScoringSchemeRequest, UpdateScoringSchemeRequest

class ScoringSchemeServiceInterface(Protocol):
  def create_scoring_scheme(self, user_id: uuid.UUID, payload: CreateScoringSchemeRequest) -> ScoringScheme:
    ...

  def list_scoring_schemes_by_user_id(self, user_id: uuid.UUID) -> list[ScoringScheme]:
    ...

  def get_scoring_scheme_by_user_id_and_id(self, scoring_scheme_id: int, user_id: uuid.UUID) -> ScoringScheme:
    ...

  def get_scoring_scheme_by_id(self, scoring_scheme_id: int) -> ScoringScheme:
    ...

  def get_usable_scoring_scheme_by_id(self, scoring_scheme_id: int, user_id: uuid.UUID) -> ScoringScheme:
    ...

  def update_scoring_scheme(self, scoring_scheme_id: int, user_id: uuid.UUID, data: UpdateScoringSchemeRequest) -> ScoringScheme:
    ...

  def delete_scoring_scheme(self, scoring_scheme_id: int, user_id: uuid.UUID) -> None:
    ...
