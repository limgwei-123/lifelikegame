"""Start player progression with empty first-completion history.

Revision ID: f2b8d6a0c413
Revises: e8a4c2b6d901
"""
from alembic import op
import sqlalchemy as sa

revision = 'f2b8d6a0c413'
down_revision = 'e8a4c2b6d901'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Intentionally no backfill from old DONE rows or point ledgers.
    op.create_table(
        'task_completions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('task_instance_id', sa.Integer(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_local_date', sa.Date(), nullable=False),
        sa.Column('timezone', sa.String(64), nullable=False),
        sa.Column('is_goal_task', sa.Boolean(), nullable=False),
        sa.UniqueConstraint('task_instance_id', name='uq_task_completions_instance'),
        sa.CheckConstraint('task_instance_id > 0', name='ck_task_completions_positive_instance'),
    )
    op.create_index('ix_task_completions_user_date', 'task_completions', ['user_id', 'completed_local_date'])


def downgrade() -> None:
    op.execute(sa.text('LOCK TABLE task_completions IN ACCESS EXCLUSIVE MODE'))
    if op.get_context().as_sql:
        # Offline downgrade SQL must also refuse to discard earned progress.
        op.execute(sa.text("""DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM task_completions LIMIT 1) THEN
            RAISE EXCEPTION 'Cannot downgrade while completion history exists';
          END IF;
        END $$;"""))
    else:
        records = sa.table('task_completions', sa.column('id', sa.Integer))
        if op.get_bind().scalar(sa.select(records.c.id).limit(1)) is not None:
            raise RuntimeError('Cannot downgrade while completion history exists; no records were changed.')
    op.drop_index('ix_task_completions_user_date', table_name='task_completions')
    op.drop_table('task_completions')
