from typing import Protocol

class ScoringSchemeServiceInterface(Protocol):
  def create_scoring_scheme(self, user_id, payload):
    ...

  def list_scoring_schemes_by_user_id(self, user_id):
    ...

  def get_scoring_scheme_by_id(self, scoring_scheme_id, user_id):
    ...

  def update_scoring_scheme(self, scoring_scheme_id, user_id, data):
    ...

  def delete_scoring_scheme(self, scoring_scheme_id, user_id):
    ...