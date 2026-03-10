import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient


sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app
from app.db import Base, engine, get_db, SessionLocal

from app.users.models import User

@pytest.fixture(scope="session", autouse=True)
def create_tables():
   Base.metadata.create_all(bind=engine)
   yield
   Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db():
    db = SessionLocal()
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