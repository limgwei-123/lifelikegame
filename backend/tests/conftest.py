import pytest
import sys
import os
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app
from app.db import Base, get_db

from app.users.models import User

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@127.0.0.1:5433/lifelikegame_test"
)



test_engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine
)

@pytest.fixture(scope="session", autouse=True)
def create_tables():
   Base.metadata.create_all(bind=test_engine)
   yield
   Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def db():
    db = TestingSessionLocal()
    yield db
    db.rollback()
    db.close()

@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()

@pytest.fixture
def test_user(client):

    user = {
        "email": "test@test.com",
        "password": "password123"
    }

    client.post("/auth/signup", json=user)

    return user


@pytest.fixture
def access_token(client,test_user):
  login_response = client.post(
        "/auth/login",
        json=test_user,
    )

  data = login_response.json()
  return data["access_token"]