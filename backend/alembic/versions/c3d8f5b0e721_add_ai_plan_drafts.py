"""add AI plan drafts

Revision ID: c3d8f5b0e721
Revises: b2c7e4a9d610
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c3d8f5b0e721"
down_revision = "b2c7e4a9d610"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_plan_drafts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("plan_json", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_ai_plan_drafts_user_created", "ai_plan_drafts", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_table("ai_plan_drafts")
