import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
  from app.models import *
class User(Base):
  __tablename__ = "users"

  id: Mapped[uuid.UUID] = mapped_column(
    UUID(as_uuid=True),
    primary_key = True,
    default= uuid.uuid4
  )

  email: Mapped[str] = mapped_column(
    String(255),
    unique= True,
    index= True,
    nullable = False
  )

  password_hash: Mapped[str] = mapped_column(
    String(255),
    nullable=False
  )

  timezone: Mapped[str] = mapped_column(
    String(64),
    default="Asia/Kuala_Lumpur"
  )

  created_at: Mapped[datetime] = mapped_column(
    DateTime,
    default=datetime.now
  )

  goals: Mapped[list["Goal"]] = relationship("Goal", back_populates="user")
  tasks: Mapped[list["Task"]] = relationship("Task", back_populates="user")
  task_schedules: Mapped[list["TaskSchedule"]] = relationship("TaskSchedule", back_populates="user")
  task_instances: Mapped[list["TaskInstance"]] = relationship("TaskInstance", back_populates="user")