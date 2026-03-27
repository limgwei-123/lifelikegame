import uuid
from datetime import date
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, DateTime, Integer, String, Text, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.db import Base

if TYPE_CHECKING:
  from app.models import *

class PointLedger(Base):
  __tablename__ = "point_ledgers"

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

  delta: Mapped[int] = mapped_column(
    Integer,
    nullable=False
  )

  entry_type: Mapped[str] = mapped_column(
    String(50),
    nullable=False,
    index=True
  )

  source_type: Mapped[str] = mapped_column(
    String(50),
    nullable=True,
    index=True
  )

  source_id: Mapped[int] = mapped_column(
    Integer,
    nullable=True,
    index=True
  )

  description: Mapped[str | None] = mapped_column(
    Text,
    nullable=True
  )

  event_at: Mapped[date] = mapped_column(
    Date,
    default=date.today
  )

  created_at: Mapped[datetime] = mapped_column(
    DateTime,
    default=datetime.now
  )

  user: Mapped["User"] = relationship("User", back_populates="point_ledgers")