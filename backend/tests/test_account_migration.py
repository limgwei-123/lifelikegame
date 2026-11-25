from datetime import date, datetime, timezone
from io import StringIO
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.core.config import get_settings

BACKEND = Path(__file__).resolve().parents[1]
PREVIOUS = 'f2b8d6a0c413'
REVISION = 'a7c9e2d4b610'


@pytest.fixture
def account_database(db, monkeypatch):
    bind, schema = db.get_bind(), 'account_' + uuid4().hex
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
        with engine.begin() as connection:
            users = sa.Table('users', sa.MetaData(), autoload_with=connection)
            user_id = uuid4()
            connection.execute(users.insert().values(id=user_id, email='legacy@example.com',
                password_hash='preserved-hash', timezone='UTC', current_value=23, created_at=datetime(2026, 1, 1)))
            facts = sa.Table('task_completions', sa.MetaData(), autoload_with=connection)
            connection.execute(facts.insert().values(user_id=user_id, task_instance_id=123,
                completed_at=datetime(2026, 1, 2, tzinfo=timezone.utc), completed_local_date=date(2026, 1, 2),
                timezone='UTC', is_goal_task=True))
        yield engine, config, user_id
    finally:
        engine.dispose()
        with bind.begin() as connection:
            connection.execute(sa.schema.DropSchema(schema, cascade=True))


def rows(engine, table):
    with engine.connect() as connection:
        reflected = sa.Table(table, sa.MetaData(), autoload_with=connection)
        return [dict(row) for row in connection.execute(sa.select(reflected)).mappings()]


def test_account_upgrade_preserves_user_password_points_and_progress_and_default_downgrade(account_database):
    engine, config, user_id = account_database
    before, history = rows(engine, 'users'), rows(engine, 'task_completions')
    command.upgrade(config, REVISION)
    upgraded = rows(engine, 'users')[0]
    assert {key: upgraded[key] for key in before[0]} == before[0]
    assert upgraded['display_name'] is None and upgraded['avatar_key'] == 'leaf' and upgraded['auth_version'] == 0
    assert rows(engine, 'task_completions') == history
    with pytest.raises(sa.exc.IntegrityError):
        with engine.begin() as connection:
            connection.execute(sa.text('UPDATE users SET auth_version=-1'))
    command.downgrade(config, PREVIOUS)
    assert rows(engine, 'users') == before and rows(engine, 'task_completions') == history
    assert ScriptDirectory(str(BACKEND / 'alembic')).get_heads() == [REVISION]


@pytest.mark.parametrize('field,value', [('display_name', 'Player'), ('avatar_key', 'sun'), ('auth_version', 1)])
@pytest.mark.parametrize('offline', [False, True])
def test_account_downgrade_refuses_losing_profile_or_resetting_revocation(account_database, field, value, offline):
    engine, config, user_id = account_database
    command.upgrade(config, REVISION)
    with engine.begin() as connection:
        users = sa.Table('users', sa.MetaData(), autoload_with=connection)
        connection.execute(users.update().values(**{field: value}))
    before = rows(engine, 'users')
    if offline:
        output = StringIO()
        config.output_buffer = output
        command.downgrade(config, f'{REVISION}:{PREVIOUS}', sql=True)
        with pytest.raises(sa.exc.DBAPIError, match='account data'):
            with engine.begin() as connection:
                connection.exec_driver_sql(output.getvalue())
    else:
        with pytest.raises(RuntimeError, match='account data'):
            command.downgrade(config, PREVIOUS)
    assert rows(engine, 'users') == before
    with engine.connect() as connection:
        assert connection.scalar(sa.text('SELECT version_num FROM alembic_version')) == REVISION
