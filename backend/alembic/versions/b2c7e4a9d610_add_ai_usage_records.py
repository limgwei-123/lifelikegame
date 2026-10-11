"""add AI usage records

Revision ID: b2c7e4a9d610
Revises: 8a1d5c7e9b20
"""
from alembic import op
import sqlalchemy as sa

revision = "b2c7e4a9d610"
down_revision = "8a1d5c7e9b20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    token_columns = ("prompt_tokens", "output_tokens", "total_tokens", "cached_input_tokens", "thinking_tokens", "tool_input_tokens")
    op.create_table(
        "ai_usage_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("request_id", sa.String(128), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latency_ms", sa.Numeric(18, 3), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=True),
        *(sa.Column(name, sa.BigInteger(), nullable=True) for name in token_columns),
        sa.Column("estimated_cost", sa.Numeric(24, 12), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("price_version", sa.String(64), nullable=True),
        sa.Column("usage_scope", sa.String(32), nullable=False),
        sa.Column("cost_status", sa.String(16), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        *(sa.CheckConstraint(f"{name} >= 0", name=f"ck_ai_usage_{name}") for name in token_columns),
        sa.CheckConstraint("latency_ms >= 0", name="ck_ai_usage_latency"),
        sa.CheckConstraint("estimated_cost >= 0", name="ck_ai_usage_cost"),
        sa.CheckConstraint("attempts >= 1 AND retry_count >= 0", name="ck_ai_usage_attempts"),
        sa.CheckConstraint("retry_count = attempts - 1", name="ck_ai_usage_retries"),
        sa.CheckConstraint("outcome IN ('success', 'error')", name="ck_ai_usage_outcome"),
        sa.CheckConstraint("usage_scope = 'reported_response'", name="ck_ai_usage_scope"),
        sa.CheckConstraint("cost_status IN ('unknown', 'estimated', 'partial')", name="ck_ai_usage_cost_status"),
    )
    op.create_index("ix_ai_usage_user_started", "ai_usage_records", ["user_id", "started_at"])
    op.create_index("ix_ai_usage_provider_model_started", "ai_usage_records", ["provider", "model", "started_at"])


def downgrade() -> None:
    op.drop_table("ai_usage_records")
