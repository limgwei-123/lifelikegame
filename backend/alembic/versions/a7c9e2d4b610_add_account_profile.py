"""Persist profile preferences and password credential revocation.

Revision ID: a7c9e2d4b610
Revises: f2b8d6a0c413
"""
from alembic import op
import sqlalchemy as sa

revision = 'a7c9e2d4b610'
down_revision = 'f2b8d6a0c413'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('display_name', sa.String(30), nullable=True))
    op.add_column('users', sa.Column('avatar_key', sa.String(20), server_default='leaf', nullable=False))
    op.add_column('users', sa.Column('auth_version', sa.Integer(), server_default='0', nullable=False))
    op.create_check_constraint('ck_users_auth_version_nonnegative', 'users', 'auth_version >= 0')


def downgrade() -> None:
    # Dropping version information would make revoked legacy tokens valid again.
    op.execute(sa.text('LOCK TABLE users IN ACCESS EXCLUSIVE MODE'))
    predicate = "display_name IS NOT NULL OR avatar_key <> 'leaf' OR auth_version <> 0"
    if op.get_context().as_sql:
        op.execute(sa.text(f"""DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM users WHERE {predicate}) THEN
            RAISE EXCEPTION 'Cannot downgrade while account data exists';
          END IF;
        END $$;"""))
    elif op.get_bind().scalar(sa.text(f'SELECT 1 FROM users WHERE {predicate} LIMIT 1')) is not None:
        raise RuntimeError('Cannot downgrade while account data exists; no records were changed.')
    op.drop_constraint('ck_users_auth_version_nonnegative', 'users', type_='check')
    op.drop_column('users', 'auth_version')
    op.drop_column('users', 'avatar_key')
    op.drop_column('users', 'display_name')
