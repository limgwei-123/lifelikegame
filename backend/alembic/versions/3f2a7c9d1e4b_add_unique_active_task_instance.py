"""add unique active task instance

Revision ID: 3f2a7c9d1e4b
Revises: 9d8c6d8ec8f0
Create Date: 2026-10-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3f2a7c9d1e4b"
down_revision: Union[str, Sequence[str], None] = "9d8c6d8ec8f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_task_instances_active_task_date",
        "task_instances",
        ["task_id", "date_instance"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_task_instances_active_task_date",
        table_name="task_instances",
    )
