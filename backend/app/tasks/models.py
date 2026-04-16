import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, String, DateTime, Text, Boolean, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models import *

class Task(Base):
   __tablename__ = "tasks"

   id: Mapped[int] = mapped_column(
    primary_key=True,
    unique=True,
    autoincrement=True,
    index=True
  )

   goal_id: Mapped[int] = mapped_column(
      ForeignKey("goals.id",ondelete="CASCADE"),
      nullable=False,
      index=True
   )

   #只是为了方便查询
   user_id: Mapped[uuid.UUID] = mapped_column(
    ForeignKey("users.id",ondelete="CASCADE"),
    nullable=False,
    index=True
  )

   title: Mapped[str] = mapped_column(
      String(255),
      nullable=False
   )
   description: Mapped[str | None] = mapped_column(Text, nullable=True)
   is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

   scoring_scheme_id: Mapped[int | None] = mapped_column(
       ForeignKey("scoring_schemes.id"),
        nullable=True,
    )

   scoring_scheme_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

   is_scoring_scheme_locked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
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

   goal: Mapped["Goal"] = relationship("Goal", back_populates="tasks")
   user: Mapped["User"] = relationship("User",back_populates="tasks")
   scoring_scheme: Mapped["ScoringScheme | None"] = relationship(
    "ScoringScheme",
    back_populates="tasks"
   )

   task_schedules: Mapped[list["TaskSchedule"]] = relationship("TaskSchedule", back_populates="task")
   task_instances: Mapped[list["TaskInstance"]] = relationship("TaskInstance", back_populates="task")
