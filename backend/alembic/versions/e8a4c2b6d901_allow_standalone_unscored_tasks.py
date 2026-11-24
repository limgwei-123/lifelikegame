"""Allow standalone unscored tasks without rewriting existing history.

Revision ID: e8a4c2b6d901
Revises: d4e9a6c1f832
"""
from alembic import op
import sqlalchemy as sa

revision = "e8a4c2b6d901"
down_revision = "d4e9a6c1f832"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("tasks", "goal_id", existing_type=sa.Integer(), nullable=True)
    op.create_check_constraint(
        "ck_tasks_standalone_unscored", "tasks",
        "goal_id IS NOT NULL OR (scoring_scheme_id IS NULL AND scoring_scheme_json IS NULL)",
    )


def downgrade() -> None:
    # Include soft-deleted rows; never delete or silently assign historical todos.
    op.execute(sa.text("LOCK TABLE tasks IN ACCESS EXCLUSIVE MODE"))
    if not op.get_context().as_sql:
        tasks = sa.table("tasks", sa.column("id", sa.Integer), sa.column("goal_id", sa.Integer))
        ids = op.get_bind().execute(
            sa.select(tasks.c.id).where(tasks.c.goal_id.is_(None)).order_by(tasks.c.id).limit(10),
        ).scalars().all()
        if ids:
            raise RuntimeError(
                f"Cannot downgrade while standalone tasks exist: ids {ids}. "
                "Resolve these records separately; no records were changed."
            )
    op.drop_constraint("ck_tasks_standalone_unscored", "tasks", type_="check")
    op.alter_column("tasks", "goal_id", existing_type=sa.Integer(), nullable=False)
