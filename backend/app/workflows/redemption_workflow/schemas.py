from pydantic import BaseModel
from datetime import datetime


from pydantic import BaseModel

class RedeemRewardRequest(BaseModel):
    pass

class RedeemRewardResponse(BaseModel):
    redemption_id: int
    reward_id: int
    reward_title: str
    cost_points: int
    remaining_points: int
    redeemed_at: datetime