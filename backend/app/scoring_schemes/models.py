import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, JSON, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
  from app.models import *

class ScoringScheme(Base):
  __tablename__ = "scoring_schemes"

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

  levels_json: Mapped[dict | None] = mapped_column(
    JSON,
    nullable=True
  )

  created_at: Mapped[datetime] = mapped_column(
    DateTime,
    default=datetime.now
  )

  updated_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    default= datetime.now,
    onupdate=datetime.now,
    nullable=False,
    )

  deleted_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
    )

  user: Mapped["User"] = relationship("User", back_populates="scoring_schemes")


  tasks: Mapped[list["Task"]] = relationship("Task", back_populates="scoring_scheme")
