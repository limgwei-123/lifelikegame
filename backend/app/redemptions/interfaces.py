from typing import Protocol

class RedemptionServiceInterface(Protocol):

  def create_redemption(self, user_id, payload):
    ...

  def list_redemptions_by_user_id(self, user_id):
    ...

  def get_redemption_by_id(self, redemption_id, user_id):
    ...