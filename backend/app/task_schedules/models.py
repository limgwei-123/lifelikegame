import uuid
from datetime import datetime,date
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, String, DateTime, Text, Enum, JSON, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.shared.enums import ScheduleType

from app.db import Base

if TYPE_CHECKING:
  from app.models import *

class TaskSchedule(Base):
  __tablename__ = "task_schedules"

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

  schedule_type:Mapped[ScheduleType] = mapped_column(
    Enum(ScheduleType, name = "schedule_type_enum"),
    nullable=False
  )

  schedule_value_json: Mapped[dict] = mapped_column(
    JSON,
    nullable=False
  )

  start_date: Mapped[date] = mapped_column(
    Date,
    nullable=True,
    default=date.today
  )

  end_date: Mapped[date] = mapped_column(
    Date,
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

  task: Mapped['Task'] = relationship("Task", back_populates="task_schedules")
  user: Mapped['User'] = relationship("User", back_populates="task_schedules")

  task_instances: Mapped[list["TaskInstance"]] = relationship("TaskInstance", back_populates="task_schedule")




