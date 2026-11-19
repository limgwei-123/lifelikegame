"""Add nonnegative reward costs and valid business states.

Revision ID: d4e9a6c1f832
Revises: c3d8f5b0e721
"""
from alembic import op
import sqlalchemy as sa


revision = "d4e9a6c1f832"
down_revision = "c3d8f5b0e721"
branch_labels = None
depends_on = None

CHECKS = (
    ("rewards", "ck_rewards_cost_points_nonnegative", "cost_points >= 0"),
    ("rewards", "ck_rewards_status", "status IN ('available', 'redeemed')"),
    ("redemptions", "ck_redemptions_cost_points_nonnegative", "cost_points >= 0"),
    ("task_instances", "ck_task_instances_status", "status IN ('todo', 'done', 'skipped')"),
)


def upgrade() -> None:
    # Stabilize the inspected rows until all constraints are installed.
    op.execute(sa.text("LOCK TABLE rewards, redemptions, task_instances IN ACCESS EXCLUSIVE MODE"))
    if not op.get_context().as_sql:
        invalid = []
        for table_name, predicate in (
            ("rewards", "cost_points < 0 OR status IS NULL OR status NOT IN ('available', 'redeemed')"),
            ("redemptions", "cost_points < 0"),
            ("task_instances", "status NOT IN ('todo', 'done', 'skipped')"),
        ):
            table = sa.table(table_name, sa.column("id", sa.Integer))
            ids = op.get_bind().execute(
                sa.select(table.c.id).where(sa.text(predicate)).order_by(table.c.id).limit(10),
            ).scalars().all()
            if ids:
                invalid.append(f"{table_name} ids {ids}")
        if invalid:
            raise RuntimeError(
                "Cannot add core business constraints: " + "; ".join(invalid)
                + ". Resolve these records separately; no records were changed."
            )
    op.alter_column("rewards", "status", existing_type=sa.String(20), nullable=False)
    for table_name, name, condition in CHECKS:
        op.create_check_constraint(name, table_name, condition)


def downgrade() -> None:
    for table_name, name, _ in reversed(CHECKS):
        op.drop_constraint(name, table_name, type_="check")
    op.alter_column("rewards", "status", existing_type=sa.String(20), nullable=True)
