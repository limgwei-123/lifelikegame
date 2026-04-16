from app.scoring_schemes.repository import ScoringSchemeRepository
from app.scoring_schemes.schemas import CreateScoringSchemeRequest, UpdateScoringSchemeRequest
from app.shared.ownership import get_owned_scoring_scheme_or_raise
from app.scoring_schemes.models import ScoringScheme

class ScoringSchemeService:
  def __init__(self, scoring_scheme_repo: ScoringSchemeRepository):
    self.scoring_scheme_repo = scoring_scheme_repo

  def create_scoring_scheme(self, user_id, payload: CreateScoringSchemeRequest):

    scoring_scheme = ScoringScheme(
      title= payload.title,
      levels_json= payload.levels_json,
      user_id = user_id
    )

    return self.scoring_scheme_repo.create(scoring_scheme)

  def list_scoring_schemes_by_user_id(self, user_id):
    return self.scoring_scheme_repo.list_by_user_id(user_id=user_id)

  def get_scoring_scheme_by_id(self, scoring_scheme_id):
    scoring_scheme = self.scoring_scheme_repo.get_by_id(scoring_scheme_id=scoring_scheme_id)
    return scoring_scheme

  def get_scoring_scheme_by_user_id_and_id(self, scoring_scheme_id, user_id):
    scoring_scheme = get_owned_scoring_scheme_or_raise(self.scoring_scheme_repo,scoring_scheme_id=scoring_scheme_id, user_id=user_id)
    return scoring_scheme

  def update_scoring_scheme(self, scoring_scheme_id, user_id, data: UpdateScoringSchemeRequest):
    scoring_scheme = get_owned_scoring_scheme_or_raise(self.scoring_scheme_repo,scoring_scheme_id=scoring_scheme_id, user_id=user_id)

    update_scoring_scheme = data.model_dump(exclude_unset=True)

    for field, value in update_scoring_scheme.items():
        setattr(scoring_scheme, field, value)

    return self.scoring_scheme_repo.update(
      scoring_scheme=scoring_scheme,
    )

  def delete_scoring_scheme(self, scoring_scheme_id, user_id):
    scoring_scheme = get_owned_scoring_scheme_or_raise(self.scoring_scheme_repo,scoring_scheme_id=scoring_scheme_id, user_id=user_id)

    self.scoring_scheme_repo.delete(scoring_scheme=scoring_scheme)