from datetime import date
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from app.errors.exception import RequestValidationError
from app.shared.enums import ScheduleType
from app.task_schedules.dependencies import build_task_schedule_service
from app.task_schedules.dtos import CreateTaskScheduleDTO
from app.task_schedules.models import TaskSchedule
from app.tasks.models import Task


def test_create_task_schedule(client, auth_headers,task):

  task_response = client.post(
    f"/tasks/{task['id']}/task_schedules",
    json={
        "schedule_type": "daily",
        "schedule_value_json": {
            "additionalProp1": {}
        },
    },
    headers=auth_headers,
  )

  print("Task Response:",task_response)
  assert task_response.status_code in (200, 201)

def test_list_task_schedules_by_task_id(client, auth_headers, task):
  task_schedules_response = client.get(
    f"/tasks/{task['id']}/task_schedules",
    headers=auth_headers
  )

  assert task_schedules_response.status_code == 200

def test_list_task_schedules_by_user_id(client, auth_headers):
  task_schedules_response = client.get(
    "/task_schedules",
    headers=auth_headers
  )

  assert task_schedules_response.status_code == 200

def test_get_task_schedule_by_id(client, auth_headers, task_schedule):


  response = client.get(
        f"/task_schedules/{task_schedule['id']}",
        headers=auth_headers
    )

  assert response.status_code == 200



def test_update_task_schedule(client, auth_headers,task_schedule):

  response = client.post(
        f"/task_schedules/{task_schedule['id']}",
        headers=auth_headers,
        json={
          "schedule_type": "daily",
          "schedule_value_json": {
            "additionalProp1": {}
          },
        }
    )

  assert response.status_code == 200

def test_delete_task_schedule(client, auth_headers, task_schedule):
  response = client.post(
      f"/task_schedules/{task_schedule['id']}/delete",
      headers=auth_headers,
  )

  assert response.status_code == 204


@pytest.mark.parametrize("value", [{}, {"days": None}, {"days": []}, {"days": 1},
                                   {"days": [-1]}, {"days": [7]}, {"days": [True]},
                                   {"days": ["1"]}, {"days": [1.5]}])
@pytest.mark.parametrize("entrypoint", ["create", "update", "workflow"])
def test_invalid_weekly_value_returns_422_without_writing(
    client, auth_headers, db, task, task_schedule, goal, scoring_scheme, value, entrypoint,
):
  with Session(db.get_bind()) as reader:
    before = (reader.query(Task).count(), reader.query(TaskSchedule).count())
  schedule = {"schedule_type": "weekly", "schedule_value_json": value}
  if entrypoint == "create":
    path, payload = f"/tasks/{task['id']}/task_schedules", schedule
  elif entrypoint == "update":
    path, payload = f"/task_schedules/{task_schedule['id']}", schedule
  else:
    path = f"/workflows/goals/{goal['id']}/tasks"
    payload = {"task": {"title": "Invalid weekly task", "scoring_scheme_id": scoring_scheme["id"]},
               "schedule": schedule}
  response = client.post(path, headers=auth_headers, json=payload)
  assert response.status_code == 422, response.text
  assert response.json()["code"] == "VALIDATION_ERROR"
  assert response.json()["details"]["issues"][0]["field"] == "schedule_value_json.days"
  with Session(db.get_bind()) as reader:
    assert (reader.query(Task).count(), reader.query(TaskSchedule).count()) == before
    row = reader.get(TaskSchedule, task_schedule["id"])
    assert row.schedule_type == ScheduleType.DAILY
    assert row.schedule_value_json == task_schedule["schedule_value_json"]


@pytest.mark.parametrize("entrypoint", ["create", "update", "workflow"])
def test_direct_schedule_api_rejects_reversed_date_range(client, auth_headers, db, task, task_schedule, entrypoint):
  payload = {"schedule_type": "daily", "schedule_value_json": {},
             "start_date": "2031-05-02", "end_date": "2031-05-01"}
  with Session(db.get_bind()) as reader:
    before = (reader.query(Task).count(), reader.query(TaskSchedule).count())
  if entrypoint == "create":
    path = f"/tasks/{task['id']}/task_schedules"
  elif entrypoint == "update":
    path = f"/task_schedules/{task_schedule['id']}"
  else:
    path = f"/workflows/goals/{task['goal_id']}/tasks"
    payload = {"task": {"title": "Invalid date range", "scoring_scheme_id": task["scoring_scheme_id"]},
               "schedule": payload}
  response = client.post(path, headers=auth_headers, json=payload)
  assert response.status_code == 422, response.text
  assert response.json()["details"]["issues"][0]["field"] == "schedule.end_date"
  with Session(db.get_bind()) as reader:
    assert (reader.query(Task).count(), reader.query(TaskSchedule).count()) == before
    row = reader.get(TaskSchedule, task_schedule["id"])
    assert row.start_date.isoformat() == task_schedule["start_date"]
    assert row.end_date is None


@pytest.mark.parametrize("value", [{"days": [True]}, {"days": ["1"]}])
def test_direct_schedule_service_rejects_coerced_weekdays(db, task, value):
  before = db.query(TaskSchedule).count()
  with pytest.raises(RequestValidationError):
    build_task_schedule_service(db).create_task_schedule(
      task_id=task["id"], user_id=UUID(task["user_id"]),
      payload=CreateTaskScheduleDTO(schedule_type=ScheduleType.WEEKLY, schedule_value_json=value),
    )
  assert db.query(TaskSchedule).count() == before


@pytest.mark.parametrize("change", [{"start_date": "2031-05-04"}, {"end_date": "2031-04-30"}])
def test_schedule_date_edit_checks_retained_dates(client, auth_headers, db, task_schedule, change):
  row = db.get(TaskSchedule, task_schedule["id"])
  row.start_date, row.end_date = date(2031, 5, 1), date(2031, 5, 3)
  db.commit()
  response = client.post(f"/task_schedules/{task_schedule['id']}", headers=auth_headers,
                         json={"schedule_type": "daily", "schedule_value_json": {}, **change})
  assert response.status_code == 422, response.text
  assert response.json()["details"]["issues"][0]["field"] == "schedule.end_date"
  with Session(db.get_bind()) as reader:
    saved = reader.get(TaskSchedule, task_schedule["id"])
    assert (saved.start_date, saved.end_date) == (date(2031, 5, 1), date(2031, 5, 3))


def test_direct_schedule_service_rejects_reversed_dates(db, task):
  before = db.query(TaskSchedule).count()
  with pytest.raises(RequestValidationError):
    build_task_schedule_service(db).create_task_schedule(
      task_id=task["id"], user_id=UUID(task["user_id"]),
      payload=CreateTaskScheduleDTO(schedule_type=ScheduleType.DAILY, schedule_value_json={},
                                    start_date=date(2031, 5, 2), end_date=date(2031, 5, 1)),
    )
  assert db.query(TaskSchedule).count() == before


@pytest.mark.parametrize("change,start,end", [
  ({"start_date": None}, None, date(2031, 5, 3)),
  ({"end_date": None}, date(2031, 5, 1), None),
  ({"start_date": "2031-05-02"}, date(2031, 5, 2), date(2031, 5, 3)),
  ({"end_date": "2031-05-04"}, date(2031, 5, 1), date(2031, 5, 4)),
])
def test_schedule_date_edit_preserves_omission_and_explicit_null(client, auth_headers, db, task_schedule, change, start, end):
  row = db.get(TaskSchedule, task_schedule["id"])
  row.start_date, row.end_date = date(2031, 5, 1), date(2031, 5, 3)
  db.commit()
  response = client.post(f"/task_schedules/{task_schedule['id']}", headers=auth_headers,
                         json={"schedule_type": "daily", "schedule_value_json": {}, **change})
  assert response.status_code == 200, response.text
  with Session(db.get_bind()) as reader:
    saved = reader.get(TaskSchedule, task_schedule["id"])
    assert saved.start_date == start
    assert saved.end_date == end


@pytest.mark.parametrize("days", [[0], [6], [0, 6]])
def test_valid_weekly_days_remain_usable(client, auth_headers, task, days):
  response = client.post(f"/tasks/{task['id']}/task_schedules", headers=auth_headers,
                         json={"schedule_type": "weekly", "schedule_value_json": {"days": days},
                               "start_date": "2031-05-01", "end_date": "2031-05-01"})
  assert response.status_code == 201, response.text
  assert response.json()["schedule_value_json"] == {"days": days}
