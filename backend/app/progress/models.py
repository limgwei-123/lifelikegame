import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TaskCompletion(Base):
    __tablename__ = 'task_completions'
    __table_args__ = (
        UniqueConstraint('task_instance_id', name='uq_task_completions_instance'),
        CheckConstraint('task_instance_id > 0', name='ck_task_completions_positive_instance'),
        Index('ix_task_completions_user_date', 'user_id', 'completed_local_date'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    # Historical source identifier, deliberately not an instance FK: task deletion
    # must neither remove earned progress nor prevent deleting the original task.
    task_instance_id: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_local_date: Mapped[date] = mapped_column(Date, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    is_goal_task: Mapped[bool] = mapped_column(Boolean, nullable=False)
