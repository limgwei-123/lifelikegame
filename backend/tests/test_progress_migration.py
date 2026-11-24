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
from app.goals.models import Goal
from app.task_instances.models import TaskInstance
from app.task_schedules.models import TaskSchedule
from app.tasks.models import Task
from app.users.models import User

BACKEND = Path(__file__).resolve().parents[1]
PREVIOUS = 'e8a4c2b6d901'
REVISION = 'f2b8d6a0c413'


@pytest.fixture
def isolated_progress_database(db, monkeypatch):
    bind, schema = db.get_bind(), 'progress_' + uuid4().hex
    assert 'test' in bind.url.database
    with bind.begin() as connection:
        connection.execute(sa.schema.CreateSchema(schema))
    url = bind.url.set(query={**bind.url.query, 'options': f'-csearch_path={schema}'})
    engine = sa.create_engine(url)
    config = Config()
    config.set_main_option('script_location', str(BACKEND / 'alembic'))
    monkeypatch.setattr(get_settings(), 'database_url', url.render_as_string(hide_password=False))
    try:
        command.upgrade(config, PREVIOUS)
        yield engine, config, schema
    finally:
        engine.dispose()
        with bind.begin() as connection:
            connection.execute(sa.schema.DropSchema(schema, cascade=True))


def legacy_instance(engine):
    with Session(engine) as session:
        user = User(email=f'progress-migration-{uuid4()}@example.com', password_hash='unused', current_value=17)
        goal = Goal(user=user, title='Old goal')
        task = Task(user=user, goal=goal, title='Old task', scoring_scheme_json={'normal': 5})
        schedule = TaskSchedule(user=user, task=task, schedule_type='daily', schedule_value_json={})
        instance = TaskInstance(user=user, task=task, task_schedule=schedule, date_instance=date(2026, 1, 1),
                                status='done', score_awarded=5, completion_level='normal', scoring_snapshot_json={'normal': 5})
        session.add_all([user, goal, task, schedule, instance])
        session.commit()
        return user.id, instance.id, task.id


def snapshots(engine):
    with engine.connect() as connection:
        return {model.__tablename__: [dict(row) for row in connection.execute(sa.select(model)).mappings()]
                for model in (User, TaskInstance, Task)}


def test_migration_starts_every_player_from_zero_without_altering_legacy_data(isolated_progress_database):
    engine, config, schema = isolated_progress_database
    legacy_instance(engine)
    before = snapshots(engine)
    command.upgrade(config, REVISION)
    from app.progress.models import TaskCompletion
    with engine.connect() as connection:
        assert connection.scalar(sa.select(sa.func.count()).select_from(TaskCompletion)) == 0
    assert snapshots(engine) == before
    inspector = sa.inspect(engine)
    foreign_keys = inspector.get_foreign_keys('task_completions', schema=schema)
    assert [(fk['referred_table'], fk['options'].get('ondelete')) for fk in foreign_keys] == [('users', 'CASCADE')]
    assert {c['name'] for c in inspector.get_unique_constraints('task_completions', schema=schema)} == {'uq_task_completions_instance'}
    command.downgrade(config, PREVIOUS)
    assert not sa.inspect(engine).has_table('task_completions', schema=schema)
    assert snapshots(engine) == before


def test_completed_history_is_unique_survives_source_deletion_and_blocks_downgrade(isolated_progress_database):
    engine, config, _ = isolated_progress_database
    user_id, instance_id, task_id = legacy_instance(engine)
    command.upgrade(config, REVISION)
    from app.progress.models import TaskCompletion
    with Session(engine) as session:
        session.add(TaskCompletion(user_id=user_id, task_instance_id=instance_id,
                                   completed_at=datetime.now(timezone.utc), completed_local_date=date(2026, 11, 24),
                                   timezone='Asia/Kuala_Lumpur', is_goal_task=True))
        session.commit()
        session.add(TaskCompletion(user_id=user_id, task_instance_id=instance_id,
                                   completed_at=datetime.now(timezone.utc), completed_local_date=date(2026, 11, 25),
                                   timezone='UTC', is_goal_task=False))
        with pytest.raises(IntegrityError, match='uq_task_completions_instance'):
            session.commit()
        session.rollback()
    with engine.begin() as connection:
        connection.execute(sa.delete(Task).where(Task.id == task_id))
    with pytest.raises(RuntimeError, match='completion history'):
        command.downgrade(config, PREVIOUS)
    with engine.connect() as connection:
        assert connection.scalar(sa.select(sa.func.count()).select_from(TaskCompletion)) == 1
        assert connection.scalar(sa.text('SELECT version_num FROM alembic_version')) == REVISION


def test_progress_migration_offline_guard_and_single_head():
    path = BACKEND / f'alembic/versions/{REVISION}_add_player_completion_history.py'
    spec = importlib.util.spec_from_file_location('progress_migration', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = StringIO()
    context = MigrationContext.configure(dialect_name='postgresql', opts={'as_sql': True, 'output_buffer': output})
    with Operations.context(context):
        module.upgrade()
        module.downgrade()
    sql = output.getvalue()
    assert 'CREATE TABLE task_completions' in sql
    assert 'uq_task_completions_instance' in sql
    assert 'RAISE EXCEPTION' in sql and 'completion history' in sql
    assert 'DROP TABLE task_completions' in sql
    assert ScriptDirectory(str(BACKEND / 'alembic')).get_heads() == [REVISION]


def test_generated_offline_downgrade_sql_really_preserves_nonempty_history(isolated_progress_database):
    engine, config, _ = isolated_progress_database
    user_id, instance_id, _ = legacy_instance(engine)
    command.upgrade(config, REVISION)
    from app.progress.models import TaskCompletion
    with Session(engine) as session:
        session.add(TaskCompletion(user_id=user_id, task_instance_id=instance_id,
                                   completed_at=datetime.now(timezone.utc), completed_local_date=date(2026, 11, 24),
                                   timezone='Asia/Kuala_Lumpur', is_goal_task=True))
        session.commit()
    path = BACKEND / f'alembic/versions/{REVISION}_add_player_completion_history.py'
    spec = importlib.util.spec_from_file_location('offline_progress_migration', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = StringIO()
    context = MigrationContext.configure(dialect_name='postgresql', opts={'as_sql': True, 'output_buffer': output})
    with Operations.context(context):
        module.downgrade()
    with pytest.raises(sa.exc.DBAPIError, match='completion history'):
        with engine.begin() as connection:
            connection.exec_driver_sql(output.getvalue())
    with engine.connect() as connection:
        assert connection.scalar(sa.select(sa.func.count()).select_from(TaskCompletion)) == 1
