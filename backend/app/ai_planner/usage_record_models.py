from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


TOKEN_COLUMNS = ("prompt_tokens", "output_tokens", "total_tokens", "cached_input_tokens", "thinking_tokens", "tool_input_tokens")


class AIUsageRecord(Base):
    __tablename__ = "ai_usage_records"
    __table_args__ = (
        *(CheckConstraint(f"{name} >= 0", name=f"ck_ai_usage_{name}") for name in TOKEN_COLUMNS),
        CheckConstraint("latency_ms >= 0", name="ck_ai_usage_latency"),
        CheckConstraint("estimated_cost >= 0", name="ck_ai_usage_cost"),
        CheckConstraint("attempts >= 1 AND retry_count >= 0", name="ck_ai_usage_attempts"),
        CheckConstraint("retry_count = attempts - 1", name="ck_ai_usage_retries"),
        CheckConstraint("outcome IN ('success', 'error')", name="ck_ai_usage_outcome"),
        CheckConstraint("usage_scope = 'reported_response'", name="ck_ai_usage_scope"),
        CheckConstraint("cost_status IN ('unknown', 'estimated', 'partial')", name="ck_ai_usage_cost_status"),
        Index("ix_ai_usage_user_started", "user_id", "started_at"),
        Index("ix_ai_usage_provider_model_started", "provider", "model", "started_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latency_ms: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attempts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    cached_input_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    thinking_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    tool_input_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(24, 12), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    price_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    usage_scope: Mapped[str] = mapped_column(String(32), nullable=False)
    cost_status: Mapped[str] = mapped_column(String(16), nullable=False)
