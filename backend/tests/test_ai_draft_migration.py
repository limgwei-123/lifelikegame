import importlib.util
from io import StringIO
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy.exc import IntegrityError

from app.ai_planner.draft_models import AIPlanDraft


BACKEND = Path(__file__).resolve().parents[1]


def load_migration():
    spec = importlib.util.spec_from_file_location("ai_draft_migration", BACKEND / "alembic/versions/c3d8f5b0e721_add_ai_plan_drafts.py")
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_draft_migration_parity_cascade_and_downgrade(db):
    migration = load_migration()
    schema = f"draft_migration_{uuid4().hex}"
    with db.get_bind().connect() as connection, connection.begin() as transaction:
        connection.execute(sa.schema.CreateSchema(schema))
        connection.execute(sa.text(f'SET LOCAL search_path TO "{schema}"'))
        users = sa.Table("users", sa.MetaData(), sa.Column("id", sa.UUID, primary_key=True))
        users.create(connection)
        user_id = uuid4()
        connection.execute(users.insert(), {"id": user_id})
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            inspector = sa.inspect(connection)
            actual = {c["name"]: (str(c["type"].compile(dialect=connection.dialect)), c["nullable"])
                      for c in inspector.get_columns("ai_plan_drafts", schema=schema)}
            expected = {c.name: (str(c.type.compile(dialect=connection.dialect)), c.nullable)
                        for c in AIPlanDraft.__table__.columns}
            assert actual == expected
            assert inspector.get_pk_constraint("ai_plan_drafts", schema=schema)["constrained_columns"] == ["id"]
            assert inspector.get_foreign_keys("ai_plan_drafts", schema=schema)[0]["options"]["ondelete"] == "CASCADE"
            assert {i["name"] for i in inspector.get_indexes("ai_plan_drafts", schema=schema)} == {i.name for i in AIPlanDraft.__table__.indexes}
            drafts = sa.Table("ai_plan_drafts", sa.MetaData(), autoload_with=connection)
            values = dict(id=uuid4(), user_id=user_id, plan_json={}, created_at=sa.func.now())
            connection.execute(drafts.insert().values(**values))
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(drafts.insert().values(**{**values, "id": uuid4(), "user_id": uuid4()}))
            connection.execute(users.delete())
            assert connection.scalar(sa.select(sa.func.count()).select_from(drafts)) == 0
            connection.execute(users.insert(), {"id": user_id})
            migration.downgrade()
            assert not sa.inspect(connection).has_table("ai_plan_drafts", schema=schema)
            assert connection.scalar(sa.select(users.c.id)) == user_id
        transaction.rollback()


def test_draft_migration_offline_and_linear_head():
    migration = load_migration()
    output = StringIO()
    with Operations.context(MigrationContext.configure(dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output})):
        migration.upgrade()
        migration.downgrade()
    assert "JSONB" in output.getvalue()
    assert "CREATE TABLE ai_plan_drafts" in output.getvalue()
    assert "DROP TABLE ai_plan_drafts" in output.getvalue()
    assert migration.down_revision == "b2c7e4a9d610"
    assert ScriptDirectory(str(BACKEND / "alembic")).get_heads() == [migration.revision]
