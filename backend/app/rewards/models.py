import uuid
from datetime import date
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, DateTime, Integer, String, Text, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.shared.enums import RewardStatus

from app.db import Base

if TYPE_CHECKING:
  from app.models import *

class Reward(Base):
  __tablename__ = "rewards"

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

  title: Mapped[str] = mapped_column(
    Text,
    nullable=True
  )

  cost_points: Mapped[int] = mapped_column(
    Integer
  )

  status: Mapped[str] = mapped_column(
    String(20),
    nullable=True,
    default=RewardStatus.AVAILABLE.value,
    server_default=RewardStatus.AVAILABLE.value,
  )

  description: Mapped[str] = mapped_column(
    Text,
    nullable=True
  )

  created_at: Mapped[datetime] = mapped_column(
    DateTime,
    default=datetime.now
  )

  updated_at: Mapped[datetime] = mapped_column(
    DateTime,
    default=datetime.now,
    onupdate=datetime.now
  )

  user: Mapped["User"] = relationship("User", back_populates="rewards")
  redemptions: Mapped[list["Redemption"]] = relationship("Redemption", back_populates="reward")