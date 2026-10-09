"""add unique reward redemption

Revision ID: 6d2f8a1c4b70
Revises: 3f2a7c9d1e4b
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6d2f8a1c4b70"
down_revision: Union[str, Sequence[str], None] = "3f2a7c9d1e4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not op.get_context().as_sql:
        redemptions = sa.table("redemptions", sa.column("reward_id", sa.Integer))
        duplicates = op.get_bind().execute(
            sa.select(redemptions.c.reward_id)
            .group_by(redemptions.c.reward_id)
            .having(sa.func.count() > 1)
            .order_by(redemptions.c.reward_id)
            .limit(10)
        ).scalars().all()
        if duplicates:
            raise RuntimeError(
                "Cannot add redemption uniqueness: duplicate reward_id values "
                f"{duplicates}. Resolve historical duplicates separately; no records were changed."
            )
    op.create_unique_constraint("uq_redemptions_reward_id", "redemptions", ["reward_id"])


def downgrade() -> None:
    op.drop_constraint("uq_redemptions_reward_id", "redemptions", type_="unique")
