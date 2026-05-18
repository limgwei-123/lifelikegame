import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, Integer
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

  current_value: Mapped[int] = mapped_column(
    Integer,
    default=0,
    nullable=True
  )

  timezone: Mapped[str] = mapped_column(
    String(64),
    default="Asia/Kuala_Lumpur"
  )

  created_at: Mapped[datetime] = mapped_column(
    DateTime,
    default=datetime.now
  )

  deleted_at: Mapped[datetime | None] = mapped_column(
         DateTime(timezone=True),
         nullable=True,
      )

  goals: Mapped[list["Goal"]] = relationship("Goal", back_populates="user", cascade="all, delete-orphan")
  tasks: Mapped[list["Task"]] = relationship("Task", back_populates="user", cascade="all, delete-orphan")
  task_schedules: Mapped[list["TaskSchedule"]] = relationship("TaskSchedule", back_populates="user", cascade="all, delete-orphan")
  task_instances: Mapped[list["TaskInstance"]] = relationship("TaskInstance", back_populates="user", cascade="all, delete-orphan")
  scoring_schemes: Mapped[list["ScoringScheme"]] = relationship("ScoringScheme", back_populates="user", cascade="all, delete-orphan")
  point_ledgers: Mapped[list["PointLedger"]] = relationship("PointLedger", back_populates="user", cascade="all, delete-orphan")
  rewards: Mapped[list["Reward"]] = relationship("Reward", back_populates="user")
  redemptions: Mapped[list["Redemption"]] = relationship("Redemption", back_populates="user", cascade="all, delete-orphan")