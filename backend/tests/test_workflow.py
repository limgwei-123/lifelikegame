import pytest

from app.task_schedules.service import TaskScheduleService
from app.tasks.models import Task


def test_create_task_with_schedule(client, auth_headers,goal,scoring_scheme):
  task_response = client.post(
    f"/workflows/goals/{goal['id']}/tasks",
    headers=auth_headers,
    json={
      "task": {
        "title": "Read every day",
        "description": "Read one chapter",
        "is_active": True,
        "scoring_scheme_id": scoring_scheme["id"],
        "is_scoring_scheme_locked": False,
      },
      "schedule": {
        "schedule_type": "once",
        "schedule_value_json": {},
        "start_date": "2026-11-01",
      },
    },
  )

  assert task_response.status_code == 201

  response_data = task_response.json()
  assert response_data["task"]["title"] == "Read every day"
  assert response_data["schedule"]["schedule_type"] == "once"
  assert response_data["schedule"]["start_date"] == "2026-11-01"
  assert response_data["task_instance"]["date_instance"] == "2026-11-01"


def test_create_task_with_schedule_rejects_invalid_command(
    client,
    auth_headers,
    goal,
    scoring_scheme,
    db,
):
  task_count_before = db.query(Task).count()

  response = client.post(
    f"/workflows/goals/{goal['id']}/tasks",
    headers=auth_headers,
    json={
      "task": {
        "title": " ",
        "scoring_scheme_id": scoring_scheme["id"],
      },
    },
  )

  assert response.status_code == 422
  assert response.json()["code"] == "VALIDATION_ERROR"
  assert db.query(Task).count() == task_count_before


def test_create_task_with_schedule_rolls_back_when_schedule_creation_fails(
    client,
    auth_headers,
    goal,
    scoring_scheme,
    db,
    monkeypatch,
):
  def fail_schedule_creation(self, task_id, user_id, payload):
    raise RuntimeError("schedule creation failed")

  monkeypatch.setattr(
    TaskScheduleService,
    "create_task_schedule",
    fail_schedule_creation,
  )
  task_count_before = db.query(Task).count()

  with pytest.raises(RuntimeError, match="schedule creation failed"):
    client.post(
      f"/workflows/goals/{goal['id']}/tasks",
      headers=auth_headers,
      json={
        "task": {
          "title": "Must be rolled back",
          "scoring_scheme_id": scoring_scheme["id"],
        },
        "schedule": {
          "schedule_type": "daily",
          "schedule_value_json": {},
          "start_date": "2026-11-01",
        },
      },
    )

  assert db.query(Task).count() == task_count_before
  assert db.query(Task).filter(Task.title == "Must be rolled back").first() is None

def test_redemption_workflow(client, auth_headers, reward):
  redemption_response = client.post(
    f"/workflows/rewards/{reward['id']}/redeem",
    headers=auth_headers,
  )

  assert redemption_response.status_code in (200, 201)
