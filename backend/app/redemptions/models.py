import uuid
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, DateTime, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.db import Base

if TYPE_CHECKING:
  from app.models import *

class Redemption(Base):
  __tablename__ = "redemptions"

  id: Mapped[int] = mapped_column(
    primary_key=True,
    unique=True,
    autoincrement=True,
    index=True
  )

  user_id: Mapped[uuid.UUID] = mapped_column(
  ForeignKey("users.id",ondelete="CASCADE"),
  nullable=False,
  index=True
)

  reward_id: Mapped[int] = mapped_column(
    ForeignKey("rewards.id"),
    nullable=False,
    index=True
  )

  reward_snapshot_json: Mapped[dict | None] = mapped_column(
    JSON,
    nullable=True
  )

  cost_points: Mapped[int] = mapped_column(
    Integer,
    nullable=False
  )

  created_at: Mapped[datetime] = mapped_column(
    DateTime,
    default=datetime.now
  )

  user: Mapped["User"] = relationship("User", back_populates="redemptions")
  reward: Mapped["Reward"] = relationship("Reward",
                                          back_populates="redemptions")