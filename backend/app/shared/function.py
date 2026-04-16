from app.scoring_schemes.interfaces import ScoringSchemeServiceInterface
from app.shared.default import SCORING_SCHME_ID

def get_scoring_scheme_workflow(scoring_scheme_id,scoring_scheme_service: ScoringSchemeServiceInterface):

  scoring_scheme = scoring_scheme_service.get_scoring_scheme_by_id(scoring_scheme_id)
  if not scoring_scheme:
    scoring_scheme_id = SCORING_SCHME_ID.DEFAULT

  scoring_scheme = scoring_scheme_service.get_scoring_scheme_by_id(scoring_scheme_id)
  return scoring_scheme