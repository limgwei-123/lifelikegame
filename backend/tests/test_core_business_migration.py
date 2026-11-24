import importlib.util
from datetime import date, datetime, timezone
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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import Base
from app.goals.models import Goal
from app.redemptions.models import Redemption
from app.rewards.models import Reward
from app.task_instances.models import TaskInstance
from app.task_schedules.models import TaskSchedule
from app.tasks.models import Task
from app.users.models import User


BACKEND = Path(__file__).resolve().parents[1]
PREVIOUS = "c3d8f5b0e721"
REVISION = "d4e9a6c1f832"


@pytest.fixture
def isolated_database(db, monkeypatch, request):
    schema = f"core_constraints_{uuid4().hex}"
    bind = db.get_bind()
    assert "test" in bind.url.database
    with bind.begin() as connection:
        connection.execute(sa.schema.CreateSchema(schema))
    query = {**bind.url.query, "options": f"-csearch_path={schema}"}
    url = bind.url.set(query=query)
    engine = sa.create_engine(url)
    config = Config()
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    monkeypatch.setattr(get_settings(), "database_url", url.render_as_string(hide_password=False))
    try:
        if getattr(request, "param", PREVIOUS) != "base":
            command.upgrade(config, PREVIOUS)
        yield engine, config, schema
    finally:
        engine.dispose()
        with bind.begin() as connection:
            connection.execute(sa.schema.DropSchema(schema, cascade=True))


def seed_history(engine):
    with Session(engine) as session:
        user = User(email=f"migration-{uuid4()}@example.com", password_hash="unused")
        goal = Goal(user=user, title="Existing goal")
        task = Task(user=user, goal=goal, title="Existing task", scoring_scheme_json={"normal": 1})
        schedule = TaskSchedule(user=user, task=task, schedule_type="daily", schedule_value_json={})
        instance = TaskInstance(user=user, task=task, task_schedule=schedule,
                                date_instance=date(2031, 1, 1), scoring_snapshot_json={"normal": 1})
        reward = Reward(user=user, title="Existing reward", cost_points=10)
        redemption = Redemption(user=user, reward=reward, cost_points=0, reward_snapshot_json={"title": "History"})
        session.add_all([user, goal, task, schedule, instance, reward, redemption])
        session.flush()
        ids = {"rewards": reward.id, "redemptions": redemption.id, "task_instances": instance.id}
        session.commit()
        return ids


def snapshot(engine):
    with engine.connect() as connection:
        return {model.__tablename__: [dict(row) for row in connection.execute(
            sa.select(model.__table__).order_by(model.id),
        ).mappings()] for model in (Reward, Redemption, TaskInstance)}


@pytest.mark.parametrize("isolated_database", ["base", PREVIOUS], indirect=True)
def test_full_history_upgrade_constraints_fk_parity_and_downgrade(isolated_database):
    engine, config, schema = isolated_database
    previous = sa.inspect(engine).has_table("rewards", schema=schema)
    before = None
    if previous:
        seed_history(engine)
        before = snapshot(engine)
    command.upgrade(config, "head")
    if before is not None:
        assert snapshot(engine) == before
    else:
        seed_history(engine)
        before = snapshot(engine)

    inspector = sa.inspect(engine)
    for table in Base.metadata.sorted_tables:
        expected = {(tuple(fk.columns.keys()), fk.referred_table.name,
                     tuple(item.column.name for item in fk.elements), fk.ondelete or "NO ACTION")
                    for fk in table.foreign_key_constraints}
        actual = {(tuple(fk["constrained_columns"]), fk["referred_table"],
                   tuple(fk["referred_columns"]), fk["options"].get("ondelete", "NO ACTION"))
                  for fk in inspector.get_foreign_keys(table.name, schema=schema)}
        assert actual == expected, table.name
    for model in (Reward, Redemption, TaskInstance):
        actual = {c["name"] for c in inspector.get_check_constraints(model.__tablename__, schema=schema)}
        expected = {c.name for c in model.__table__.constraints if isinstance(c, sa.CheckConstraint)}
        assert actual == expected
    assert next(c for c in inspector.get_columns("rewards", schema=schema) if c["name"] == "status")["nullable"] is False

    with engine.begin() as connection:
        for table, column, value in [(Reward, "cost_points", -1), (Reward, "status", "invalid"),
                                     (Redemption, "cost_points", -1), (TaskInstance, "status", "invalid")]:
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(sa.update(table).values(**{column: value}))
    assert snapshot(engine) == before
    command.downgrade(config, PREVIOUS)
    assert snapshot(engine) == before
    inspector = sa.inspect(engine)
    for model in (Reward, Redemption, TaskInstance):
        assert inspector.get_check_constraints(model.__tablename__, schema=schema) == []
    assert next(c for c in inspector.get_columns("rewards", schema=schema) if c["name"] == "status")["nullable"] is True


@pytest.mark.parametrize("table_name,column,value,correct", [
    ("rewards", "cost_points", -1, 10),
    ("rewards", "status", None, "available"),
    ("rewards", "status", "invalid", "available"),
    ("redemptions", "cost_points", -1, 0),
    ("task_instances", "status", "completed", "todo"),
])
def test_upgrade_refuses_invalid_history_without_changing_records(isolated_database, table_name, column, value, correct):
    engine, config, schema = isolated_database
    ids = seed_history(engine)
    table = Base.metadata.tables[table_name]
    with engine.begin() as connection:
        connection.execute(table.update().where(table.c.id == ids[table_name]).values(**{column: value}))
    before = snapshot(engine)
    with pytest.raises(RuntimeError, match=f"{table_name} ids"):
        command.upgrade(config, "head")
    assert snapshot(engine) == before
    with engine.connect() as connection:
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == PREVIOUS
    assert sa.inspect(engine).get_check_constraints("rewards", schema=schema) == []
    # A separate, explicit operator repair permits retry; the migration never repairs data.
    with engine.begin() as connection:
        connection.execute(table.update().where(table.c.id == ids[table_name]).values(**{column: correct}))
    command.upgrade(config, "head")


def test_constraint_migration_offline_sql_and_single_head():
    path = BACKEND / f"alembic/versions/{REVISION}_add_core_business_constraints.py"
    spec = importlib.util.spec_from_file_location("core_business_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    output = StringIO()
    context = MigrationContext.configure(dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output})
    with Operations.context(context):
        migration.upgrade()
        migration.downgrade()
    sql = output.getvalue()
    assert "LOCK TABLE rewards, redemptions, task_instances" in sql
    assert "ALTER COLUMN status SET NOT NULL" in sql
    assert "ck_redemptions_cost_points_nonnegative" in sql
    assert "DROP CONSTRAINT ck_task_instances_status" in sql
    scripts = ScriptDirectory(str(BACKEND / "alembic"))
    heads = scripts.get_heads()
    assert len(heads) == 1
    assert REVISION in {item.revision for item in scripts.iterate_revisions(heads[0], "base")}


def test_upgrade_reports_invalid_soft_deleted_history_across_tables(isolated_database):
    engine, config, schema = isolated_database
    ids = seed_history(engine)
    deleted_at = datetime.now(timezone.utc)
    with engine.begin() as connection:
        for model, values in (
            (Reward, {"cost_points": -1}), (Redemption, {"cost_points": -2}),
            (TaskInstance, {"status": "completed"}),
        ):
            connection.execute(sa.update(model).where(model.id == ids[model.__tablename__])
                               .values(**values, deleted_at=deleted_at))
    before = snapshot(engine)
    with pytest.raises(RuntimeError) as error:
        command.upgrade(config, "head")
    for table_name, row_id in ids.items():
        assert f"{table_name} ids [{row_id}]" in str(error.value)
    assert snapshot(engine) == before
    with engine.connect() as connection:
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == PREVIOUS
    assert sa.inspect(engine).get_check_constraints("rewards", schema=schema) == []
