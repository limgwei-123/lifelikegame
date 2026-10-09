import importlib.util
from io import StringIO
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.exc import IntegrityError


MIGRATION_PATH = (Path(__file__).resolve().parents[1] / "alembic" / "versions"
                  / "6d2f8a1c4b70_add_unique_reward_redemption.py")
spec = importlib.util.spec_from_file_location("redemption_uniqueness_migration", MIGRATION_PATH)
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


@pytest.fixture
def migration_table(db):
    # A transactional temporary table shadows public.redemptions on this connection only.
    with db.get_bind().connect() as connection:
        transaction = connection.begin()
        try:
            table = sa.Table(
                "redemptions", sa.MetaData(),
                sa.Column("id", sa.Integer, primary_key=True),
                sa.Column("reward_id", sa.Integer, nullable=False),
                prefixes=["TEMPORARY"],
            )
            table.create(connection)
            with Operations.context(MigrationContext.configure(connection)):
                yield connection, table
        finally:
            transaction.rollback()


def test_migration_adds_uniqueness_and_downgrade_removes_it(migration_table):
    connection, table = migration_table
    connection.execute(table.insert(), {"id": 1, "reward_id": 7})
    migration.upgrade()
    with pytest.raises(IntegrityError), connection.begin_nested():
        connection.execute(table.insert(), {"id": 2, "reward_id": 7})
    migration.downgrade()
    connection.execute(table.insert(), {"id": 2, "reward_id": 7})
    assert connection.scalar(sa.select(sa.func.count()).select_from(table)) == 2


def test_migration_refuses_historical_duplicates_without_changing_records(migration_table):
    connection, table = migration_table
    connection.execute(table.insert(), [{"id": 1, "reward_id": 7}, {"id": 2, "reward_id": 7}])
    with pytest.raises(RuntimeError, match=r"duplicate reward_id values \[7\]"):
        migration.upgrade()
    assert connection.execute(sa.select(table).order_by(table.c.id)).all() == [(1, 7), (2, 7)]
    connection.execute(table.insert(), {"id": 3, "reward_id": 7})


def test_migration_can_generate_offline_sql():
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output},
    )
    with Operations.context(context):
        migration.upgrade()
        migration.downgrade()
    assert "ADD CONSTRAINT uq_redemptions_reward_id UNIQUE (reward_id)" in output.getvalue()
    assert "DROP CONSTRAINT uq_redemptions_reward_id" in output.getvalue()
