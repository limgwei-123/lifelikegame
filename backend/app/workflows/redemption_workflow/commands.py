from dataclasses import dataclass
import uuid

from app.core.cqrs import TransactionalCommand


@dataclass(frozen=True, slots=True, kw_only=True)
class RedeemRewardCommand(TransactionalCommand):
  reward_id: int
  user_id: uuid.UUID
