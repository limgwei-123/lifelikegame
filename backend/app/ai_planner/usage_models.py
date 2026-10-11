from datetime import date
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AIDailyUsage(Base):
    __tablename__ = "ai_daily_usage"
    __table_args__ = (CheckConstraint("request_count >= 0", name="ck_ai_daily_usage_count"),)

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True,
    )
    usage_date: Mapped[date] = mapped_column(Date, primary_key=True)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
