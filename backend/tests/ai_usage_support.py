from uuid import uuid4

import pytest

from app.users.models import User


@pytest.fixture
def ai_user_ids(db):
    users = [User(email=f"ai-{uuid4()}@example.com", password_hash="unused") for _ in range(2)]
    db.add_all(users)
    db.flush()
    ids = [user.id for user in users]
    db.commit()
    return ids
