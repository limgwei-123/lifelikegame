"""Seed historical user schemas without depending on current ORM columns."""
from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa


def seed_legacy_user(session, **values):
    table = sa.Table('users', sa.MetaData(), autoload_with=session.connection())
    payload = dict(id=uuid4(), email=f'migration-{uuid4()}@example.com', password_hash='unused',
                   timezone='Asia/Kuala_Lumpur', current_value=0, created_at=datetime(2026, 1, 1))
    payload.update(values)
    session.execute(table.insert().values(**payload))
    return payload['id']
