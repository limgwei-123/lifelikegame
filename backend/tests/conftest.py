import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient


sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app

class FakeUser:
    def __init__(self, id, email):
        self.id = id
        self.email = email

@pytest.fixture
def client():
  return TestClient(app)

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
  client.post(
        "/auth/signup",
        json=test_user,
    )

  login_response = client.post(
        "/auth/login",
        json=test_user,
    )

  data = login_response.json()
  return data["access_token"]