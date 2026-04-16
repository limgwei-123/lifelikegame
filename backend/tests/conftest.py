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


TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL"
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
def auth_user(client):

    user = {
        "email": "auth@auth.com",
        "password": "password123"
    }

    client.post("/auth/signup", json=user)

    login = client.post("/auth/login", json=user).json()

    token = login["access_token"]

    me = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"}
    ).json()

    return {
        "access_token": token,
        "user_id": me["id"]
    }

@pytest.fixture
def auth_headers(auth_user):
    return {
        "Authorization": f"Bearer {auth_user['access_token']}"
    }

@pytest.fixture
def goal(client, auth_headers):
    res = client.post(
        "/goals",
        json={
            "title": "Test Goal",
            "start_date": "2026-03-14"
        },
        headers=auth_headers,
    )
    assert res.status_code in (200, 201)
    return res.json()

@pytest.fixture
def scoring_scheme(client, auth_headers):
    res = client.post(
    "/scoring_schemes",
    headers=auth_headers,
    json={
    "title": "normal",
    "levels_json": {
        "normal": 1,
        "good": 2,
        "perfect": 3
    }
    }
    )

    assert res.status_code in (200, 201)
    return res.json()

@pytest.fixture
def task(client, auth_headers,goal,scoring_scheme):
    res = client.post(
        f"/goals/{goal['id']}/tasks",
        json={
            "title": "Test Task",
            "scoring_scheme_id": scoring_scheme['id']
        },
        headers=auth_headers,
    )
    assert res.status_code in (200, 201)
    return res.json()

@pytest.fixture
def task_schedule(client, auth_headers,task):
    res = client.post(
        f"/tasks/{task['id']}/task_schedules",
        json={
            "schedule_type": "daily",
            "schedule_value_json": {
                "additionalProp1": {}
            },
            "start_date": "2026-04-15",
        },
        headers=auth_headers,
    )
    assert res.status_code in (200, 201)
    return res.json()

@pytest.fixture
def task_instance(client, auth_headers, task, task_schedule):
    res = client.post(
        f"/tasks/{task['id']}/task_schedules/{task_schedule['id']}/task_instances",
        json={
            "date_instance": "2026-04-16",
            "scoring_snapshot_json":{

            }
        },
        headers=auth_headers,
    )

    assert res.status_code in (200, 201)
    return res.json()



@pytest.fixture
def reward(client, auth_headers):
    res = client.post(
    "/rewards",
    headers=auth_headers,
    json={
    "title": "First Reward",
    "cost_points": 2
    }
    )

    assert res.status_code in (200, 201)
    return res.json()


@pytest.fixture
def redemption(client, auth_headers,reward):
    res = client.post(
    "/redemptions",
    headers=auth_headers,
    json={
    "reward_id": reward['id'],
    }
    )

    assert res.status_code in (200, 201)
    return res.json()