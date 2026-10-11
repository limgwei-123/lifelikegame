import importlib.util
from datetime import date
from io import StringIO
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy.exc import IntegrityError


BACKEND = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "ai_usage_migration", BACKEND / "alembic/versions/8a1d5c7e9b20_add_ai_daily_usage.py",
)
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


def test_migration_constraints_and_downgrade_in_isolated_schema(db):
    # PostgreSQL transactional DDL makes the entire private schema disposable.
    schema = f"ai_migration_{uuid4().hex}"
    with db.get_bind().connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(sa.schema.CreateSchema(schema))
            connection.execute(sa.text(f'SET LOCAL search_path TO "{schema}"'))
            users = sa.Table("users", sa.MetaData(), sa.Column("id", sa.UUID, primary_key=True))
            users.create(connection)
            user_id = uuid4()
            connection.execute(users.insert(), {"id": user_id})
            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()
                inspector = sa.inspect(connection)
                assert set(inspector.get_pk_constraint("ai_daily_usage", schema=schema)["constrained_columns"]) == {"user_id", "usage_date"}
                assert inspector.get_foreign_keys("ai_daily_usage", schema=schema)[0]["options"]["ondelete"] == "CASCADE"
                usage = sa.Table("ai_daily_usage", sa.MetaData(), autoload_with=connection)
                record = {"user_id": user_id, "usage_date": date(2026, 10, 11), "request_count": 1}
                connection.execute(usage.insert(), record)
                for invalid in (record, dict(record, request_count=-1, usage_date=date(2026, 10, 12)), dict(record, user_id=uuid4())):
                    with pytest.raises(IntegrityError), connection.begin_nested():
                        connection.execute(usage.insert(), invalid)
                connection.execute(users.delete().where(users.c.id == user_id))
                assert connection.scalar(sa.select(sa.func.count()).select_from(usage)) == 0
                connection.execute(users.insert(), {"id": user_id})
                migration.downgrade()
                assert not sa.inspect(connection).has_table("ai_daily_usage", schema=schema)
                assert sa.inspect(connection).has_table("users", schema=schema)
                assert connection.scalar(sa.select(users.c.id)) == user_id
        finally:
            transaction.rollback()


def test_migration_offline_sql_and_single_head():
    output = StringIO()
    context = MigrationContext.configure(dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output})
    with Operations.context(context):
        migration.upgrade()
        migration.downgrade()
    sql = output.getvalue()
    assert "PRIMARY KEY (user_id, usage_date)" in sql
    assert "request_count >= 0" in sql
    assert "ON DELETE CASCADE" in sql
    assert "DROP TABLE ai_daily_usage" in sql
    assert migration.down_revision == "6d2f8a1c4b70"
    assert ScriptDirectory(str(BACKEND / "alembic")).get_heads() == [migration.revision]
