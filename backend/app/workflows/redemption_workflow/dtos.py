from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class RedeemRewardResultDTO:
  redemption_id: int
  reward_id: int
  reward_title: str
  cost_points: int
  remaining_points: int
  redeemed_at: datetime

  def __post_init__(self) -> None:
    # Nullable legacy titles must fail before the transaction commits.
    if not isinstance(self.reward_title, str):
      raise ValueError("Redeemed reward title must be a string")
