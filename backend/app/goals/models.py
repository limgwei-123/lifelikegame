import uuid
from datetime import datetime,date
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, String, Date, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.users.models import User

class Goal(Base):
  __tablename__ = "goals"

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
     String(255),
     nullable=False
  )

  start_date: Mapped[date] = mapped_column(
     Date,
     default=date.today,
     nullable=True
  )

  target_date: Mapped[date] = mapped_column(
     Date,
     nullable=True
  )

  current_value: Mapped[str] = mapped_column(
     String(255),
     nullable=True
  )

  target_value: Mapped[str] = mapped_column(
     String(255),
     nullable=True
  )

  created_at: Mapped[datetime] = mapped_column(
     DateTime,
     default=datetime.now
  )


  user: Mapped["User"] = relationship("User",back_populates="goals")
  tasks = relationship("Task", back_populates="goal", cascade="all, delete-orphan")