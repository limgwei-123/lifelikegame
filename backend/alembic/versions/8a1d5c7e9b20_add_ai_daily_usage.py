"""add AI daily usage

Revision ID: 8a1d5c7e9b20
Revises: 6d2f8a1c4b70
"""
from alembic import op
import sqlalchemy as sa

revision = "8a1d5c7e9b20"
down_revision = "6d2f8a1c4b70"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_daily_usage",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("request_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "usage_date"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("request_count >= 0", name="ck_ai_daily_usage_count"),
    )


def downgrade() -> None:
    op.drop_table("ai_daily_usage")
