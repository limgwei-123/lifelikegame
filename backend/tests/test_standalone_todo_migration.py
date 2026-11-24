import importlib.util
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.goals.models import Goal
from app.tasks.models import Task
from app.users.models import User

BACKEND = Path(__file__).resolve().parents[1]
PREVIOUS = "d4e9a6c1f832"
REVISION = "e8a4c2b6d901"


@pytest.fixture
def isolated_todo_database(db, monkeypatch):
    bind = db.get_bind()
    assert "test" in bind.url.database
    schema = f"standalone_{uuid4().hex}"
    with bind.begin() as connection:
        connection.execute(sa.schema.CreateSchema(schema))
    url = bind.url.set(query={**bind.url.query, "options": f"-csearch_path={schema}"})
    engine = sa.create_engine(url)
    config = Config()
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    monkeypatch.setattr(get_settings(), "database_url", url.render_as_string(hide_password=False))
    try:
        command.upgrade(config, PREVIOUS)
        yield engine, config, schema
    finally:
        engine.dispose()
        with bind.begin() as connection:
            connection.execute(sa.schema.DropSchema(schema, cascade=True))


def seed_task(engine, standalone=False):
    with Session(engine) as session:
        user = User(email=f"migration-todo-{uuid4()}@example.com", password_hash="unused")
        goal = None if standalone else Goal(user=user, title="Existing goal")
        task = Task(user=user, goal=goal, title="Preserved task", scoring_scheme_json=None if standalone else {"done": 5})
        session.add(task)
        session.commit()
        return task.id


def task_rows(engine):
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(sa.select(Task.__table__).order_by(Task.id)).mappings()]


def test_upgrade_preserves_goal_tasks_and_allows_unscored_standalone_tasks(isolated_todo_database):
    engine, config, schema = isolated_todo_database
    seed_task(engine)
    before = task_rows(engine)
    command.upgrade(config, REVISION)
    assert task_rows(engine) == before
    assert next(c for c in sa.inspect(engine).get_columns("tasks", schema=schema) if c["name"] == "goal_id")["nullable"]
    standalone_id = seed_task(engine, standalone=True)
    with engine.connect() as connection:
        assert connection.scalar(sa.select(Task.goal_id).where(Task.id == standalone_id)) is None
    with Session(engine) as session:
        task = session.get(Task, standalone_id)
        task.scoring_scheme_json = {"done": 999}
        with pytest.raises(IntegrityError, match="ck_tasks_standalone_unscored"):
            session.commit()
        session.rollback()
    # Deleting the test-only standalone task permits a safe downgrade without touching the historical row.
    with engine.begin() as connection:
        connection.execute(sa.delete(Task).where(Task.id == standalone_id))
    command.downgrade(config, PREVIOUS)
    assert task_rows(engine) == before


@pytest.mark.parametrize("soft_deleted", [False, True])
def test_downgrade_refuses_to_discard_or_reassign_standalone_history(isolated_todo_database, soft_deleted):
    engine, config, _ = isolated_todo_database
    command.upgrade(config, REVISION)
    task_id = seed_task(engine, standalone=True)
    if soft_deleted:
        with engine.begin() as connection:
            connection.execute(sa.update(Task).where(Task.id == task_id).values(deleted_at=datetime.now(timezone.utc)))
    before = task_rows(engine)
    with pytest.raises(RuntimeError, match="standalone tasks"):
        command.downgrade(config, PREVIOUS)
    assert task_rows(engine) == before
    with engine.connect() as connection:
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == REVISION


def test_standalone_migration_offline_sql_and_single_head():
    path = BACKEND / f"alembic/versions/{REVISION}_allow_standalone_unscored_tasks.py"
    spec = importlib.util.spec_from_file_location("standalone_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    output = StringIO()
    context = MigrationContext.configure(dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output})
    with Operations.context(context):
        migration.upgrade()
        migration.downgrade()
    sql = output.getvalue()
    assert "ALTER COLUMN goal_id DROP NOT NULL" in sql
    assert "ck_tasks_standalone_unscored" in sql
    assert "ALTER COLUMN goal_id SET NOT NULL" in sql
    scripts = ScriptDirectory(str(BACKEND / "alembic"))
    heads = scripts.get_heads()
    assert len(heads) == 1
    assert REVISION in {item.revision for item in scripts.iterate_revisions(heads[0], "base")}
