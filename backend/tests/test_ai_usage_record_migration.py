import importlib.util
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy.exc import IntegrityError

from app.ai_planner.usage_record_models import AIUsageRecord


BACKEND = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "ai_usage_record_migration", BACKEND / "alembic/versions/b2c7e4a9d610_add_ai_usage_records.py",
)
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


def test_usage_record_migration_upgrade_and_downgrade_in_private_schema(db):
    schema = f"ai_records_migration_{uuid4().hex}"
    with db.get_bind().connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(sa.schema.CreateSchema(schema))
            connection.execute(sa.text(f'SET LOCAL search_path TO "{schema}"'))
            metadata = sa.MetaData()
            users = sa.Table("users", metadata, sa.Column("id", sa.UUID, primary_key=True))
            daily = sa.Table("ai_daily_usage", metadata, sa.Column("id", sa.Integer, primary_key=True))
            metadata.create_all(connection)
            user_id = uuid4()
            connection.execute(users.insert(), {"id": user_id})
            connection.execute(daily.insert(), {"id": 1})
            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()
                inspector = sa.inspect(connection)
                columns = inspector.get_columns("ai_usage_records", schema=schema)
                actual = {c["name"]: (str(c["type"].compile(dialect=connection.dialect)), c["nullable"]) for c in columns}
                expected = {c.name: (str(c.type.compile(dialect=connection.dialect)), c.nullable) for c in AIUsageRecord.__table__.columns}
                assert actual == expected
                assert inspector.get_pk_constraint("ai_usage_records", schema=schema)["constrained_columns"] == ["id"]
                assert inspector.get_foreign_keys("ai_usage_records", schema=schema)[0]["options"]["ondelete"] == "CASCADE"
                assert {i["name"] for i in inspector.get_indexes("ai_usage_records", schema=schema)} == {i.name for i in AIUsageRecord.__table__.indexes}
                assert {c["name"] for c in inspector.get_check_constraints("ai_usage_records", schema=schema)} == {
                    c.name for c in AIUsageRecord.__table__.constraints if isinstance(c, sa.CheckConstraint)
                }
                records = sa.Table("ai_usage_records", sa.MetaData(), autoload_with=connection)
                values = dict(id=uuid4(), user_id=user_id, request_id=str(uuid4()), provider="gemini", model="test",
                              started_at=datetime.now(timezone.utc), finished_at=datetime.now(timezone.utc), latency_ms=1,
                              outcome="success", usage_scope="reported_response", cost_status="unknown", attempts=1, retry_count=0)
                connection.execute(records.insert(), values)
                for updates in ({}, {"id": uuid4(), "prompt_tokens": -1}, {"id": uuid4(), "attempts": 0},
                                {"id": uuid4(), "retry_count": 2}, {"id": uuid4(), "user_id": uuid4()}):
                    with pytest.raises(IntegrityError), connection.begin_nested():
                        connection.execute(records.insert(), {**values, **updates})
                connection.execute(users.delete())
                assert connection.scalar(sa.select(sa.func.count()).select_from(records)) == 0
                connection.execute(users.insert(), {"id": user_id})
                migration.downgrade()
                assert not sa.inspect(connection).has_table("ai_usage_records", schema=schema)
                assert connection.scalar(sa.select(users.c.id)) == user_id
                assert connection.scalar(sa.select(daily.c.id)) == 1
        finally:
            transaction.rollback()


def test_usage_record_migration_offline_sql_and_single_head():
    output = StringIO()
    context = MigrationContext.configure(dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output})
    with Operations.context(context):
        migration.upgrade()
        migration.downgrade()
    sql = output.getvalue()
    assert "CREATE TABLE ai_usage_records" in sql and "DROP TABLE ai_usage_records" in sql
    assert "ON DELETE CASCADE" in sql and "NUMERIC(24, 12)" in sql
    assert "CREATE INDEX ix_ai_usage_user_started" in sql
    assert migration.down_revision == "8a1d5c7e9b20"
    assert ScriptDirectory(str(BACKEND / "alembic")).get_heads() == [migration.revision]
