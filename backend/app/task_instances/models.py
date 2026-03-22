import uuid
from datetime import datetime,date
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, DateTime, Date, String, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base
from enum import StrEnum

if TYPE_CHECKING:
  from app.models import *


class TaskInstanceStatus(StrEnum):
  TODO = "todo"
  DONE = "done"
  SKIPPED = "skipped"

class TaskInstance(Base):
  __tablename__ = "task_instances"

  id: Mapped[int] = mapped_column(
    primary_key=True,
    unique=True,
    autoincrement=True,
    index=True
  )

  task_id: Mapped[int] = mapped_column(
    ForeignKey("tasks.id", ondelete="CASCADE"),
    nullable=False,
    index=True
  )

  #只是为了方便查询
  user_id: Mapped[uuid.UUID] = mapped_column(
    ForeignKey('users.id', ondelete="CASCADE"),
    nullable=False,
    index=True
  )

  #只是作为记录
  task_schedule_id: Mapped[int] = mapped_column(
    ForeignKey("task_schedules.id"),
    nullable=False,
    index=True
  )

  date_instance: Mapped[date] = mapped_column(
    Date,
    nullable=False
  )

  status: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default=TaskInstanceStatus.TODO.value,
    server_default=TaskInstanceStatus.TODO.value,
  )

  completion_level: Mapped[str | None] = mapped_column(
    String(200),
    nullable=True
  )

  score_awarded: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    default=0,
    server_default="0"
  )

  scoring_snapshot_json: Mapped[dict] = mapped_column(
        JSON,
        nullable=True,
    )

  generated_reason: Mapped[str | None] = mapped_column(
    String(100),
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

  task: Mapped['Task'] = relationship("Task", back_populates="task_instances")
  user: Mapped['User'] = relationship("User", back_populates="task_instances")
  task_schedule: Mapped['TaskSchedule'] = relationship("TaskSchedule", back_populates = "task_instances")