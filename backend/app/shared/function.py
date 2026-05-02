from app.scoring_schemes.interfaces import ScoringSchemeServiceInterface
from app.shared.default import SCORING_SCHME_ID

from datetime import date
from app.task_instances.interfaces import TaskInstanceServiceInterface

def get_scoring_scheme_workflow(scoring_scheme_id,scoring_scheme_service: ScoringSchemeServiceInterface):

  scoring_scheme = scoring_scheme_service.get_scoring_scheme_by_id(scoring_scheme_id)
  if not scoring_scheme:
    scoring_scheme_id = SCORING_SCHME_ID.DEFAULT

  scoring_scheme = scoring_scheme_service.get_scoring_scheme_by_id(scoring_scheme_id)
  return scoring_scheme


def generate_task_instances_for_today(task_instance_service: TaskInstanceServiceInterface):
    date_selected = date.today()
    task_instance_service.generate_task_instances_for_date(date_selected)