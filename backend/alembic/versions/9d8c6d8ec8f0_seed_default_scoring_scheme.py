"""seed default scoring scheme

Revision ID: 9d8c6d8ec8f0
Revises: 2c0f0576cb08
Create Date: 2026-05-18 13:58:46.748490

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d8c6d8ec8f0'
down_revision: Union[str, Sequence[str], None] = '2c0f0576cb08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.alter_column(
        "scoring_schemes",
        "user_id",
        nullable=True,
    )


    op.execute(
    sa.text("""
        INSERT INTO scoring_schemes (
            user_id,
            title,
            levels_json,
            created_at,
            updated_at
        )
        SELECT
            NULL,
            'Default',
            '{"perfect": 3, "normal": 2, "minimal": 1, "none": 0}'::jsonb,
            NOW(),
            NOW()
        WHERE NOT EXISTS (
            SELECT 1
            FROM scoring_schemes
            WHERE user_id IS NULL
            AND title = 'Default'
        )
    """)
)


def downgrade() -> None:
    op.execute(
        sa.text("""
            DELETE FROM scoring_schemes
            WHERE user_id IS NULL
            AND title = 'Default'
        """)
    )
