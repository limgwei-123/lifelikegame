from typing import Protocol
from app.redemptions.schemas import CreateRedemptionRequest

from app.redemptions.models import Redemption
class RedemptionServiceInterface(Protocol):

  def create_redemption(self, user_id, payload:CreateRedemptionRequest)->Redemption:
    ...

  def list_redemptions_by_user_id(self, user_id):
    ...

  def get_redemption_by_id(self, redemption_id, user_id):
    ...