from app.scoring_schemes.interfaces import ScoringSchemeServiceInterface
from app.shared.default import SCORING_SCHME_ID
from app.errors.exception import NotFoundError


def get_scoring_scheme_workflow(scoring_scheme_id,scoring_scheme_service: ScoringSchemeServiceInterface, user_id):

  if not scoring_scheme_id or scoring_scheme_id==0:
     scoring_scheme_id = SCORING_SCHME_ID.DEFAULT

  scoring_scheme = scoring_scheme_service.get_usable_scoring_scheme_by_id(scoring_scheme_id, user_id)
  if scoring_scheme is None:
    raise NotFoundError("Scoring Scheme not found")
  return scoring_scheme
