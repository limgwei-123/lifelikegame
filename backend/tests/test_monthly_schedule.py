from datetime import date
from uuid import UUID

import pytest

from app.errors.exception import RequestValidationError
from app.shared.enums import ScheduleType
from app.task_instances.commands import GenerateDailyTaskInstancesCommand
from app.task_instances.dependencies import (
    build_generate_task_instances_mediator, build_task_instance_service,
)
from app.task_instances.models import TaskInstance
from app.task_schedules.dependencies import build_task_schedule_service
from app.task_schedules.dtos import CreateTaskScheduleDTO
from app.task_schedules.models import TaskSchedule
from app.tasks.models import Task


@pytest.mark.parametrize("day,target_date,expected", [
    (29, date(2031, 2, 28), False),
    (29, date(2031, 3, 1), False),
    (29, date(2032, 2, 28), False),
    (29, date(2032, 2, 29), True),
    (29, date(2100, 2, 28), False),
    (29, date(2000, 2, 29), True),
    (30, date(2031, 2, 28), False),
    (30, date(2032, 2, 29), False),
    (30, date(2031, 4, 30), True),
    (31, date(2031, 4, 30), False),
    (31, date(2031, 5, 1), False),
    (31, date(2031, 5, 31), True),
])
def test_monthly_policy_skips_missing_days_without_catch_up(db, day, target_date, expected):
    schedule = TaskSchedule(
        schedule_type=ScheduleType.MONTHLY, schedule_value_json={"day": day},
        start_date=None, end_date=None,
    )
    service = build_task_instance_service(db)
    assert service._should_generate_for_date(schedule, target_date) is expected


def test_monthly_generation_skips_short_month_and_resumes_on_exact_date(
    client, auth_headers, db, task, task_schedule,
):
    response = client.post(
        f"/task_schedules/{task_schedule['id']}", headers=auth_headers,
        json={"schedule_type": "monthly", "schedule_value_json": {"day": 31},
              "start_date": "2031-02-01"},
    )
    assert response.status_code == 200
    mediator = build_generate_task_instances_mediator(db)
    for target_date in (date(2031, 2, 28), date(2031, 4, 30), date(2031, 5, 1)):
        result = mediator.send(GenerateDailyTaskInstancesCommand(target_date=target_date))
        assert task["id"] not in {row.task_id for row in result.task_instances}
    command = GenerateDailyTaskInstancesCommand(target_date=date(2031, 5, 31))
    result = mediator.send(command)
    instance = next(row for row in result.task_instances if row.task_id == task["id"])
    assert instance.date_instance == date(2031, 5, 31)
    mediator.send(command)
    assert db.query(TaskInstance).filter(TaskInstance.task_id == task["id"]).count() == 1


@pytest.mark.parametrize("day", [1, 29, 30, 31])
def test_monthly_days_are_valid_independent_of_start_month(
    client, auth_headers, task, day,
):
    response = client.post(
        f"/tasks/{task['id']}/task_schedules", headers=auth_headers,
        json={"schedule_type": "monthly", "schedule_value_json": {"day": day},
              "start_date": "2031-02-01"},
    )
    assert response.status_code == 201
    assert response.json()["schedule_value_json"] == {"day": day}


@pytest.mark.parametrize("value", [{}, {"day": None}, {"day": 0}, {"day": 32},
                                    {"day": True}, {"day": "31"}, {"day": 31.5}])
@pytest.mark.parametrize("entrypoint", ["create", "update", "workflow"])
def test_invalid_monthly_day_returns_422_without_writing(
    client, auth_headers, db, task, task_schedule, goal, scoring_scheme, value, entrypoint,
):
    task_count = db.query(Task).count()
    schedule_count = db.query(TaskSchedule).count()
    schedule = {"schedule_type": "monthly", "schedule_value_json": value}
    if entrypoint == "create":
        path, payload = f"/tasks/{task['id']}/task_schedules", schedule
    elif entrypoint == "update":
        path, payload = f"/task_schedules/{task_schedule['id']}", schedule
    else:
        path = f"/workflows/goals/{goal['id']}/tasks"
        payload = {"task": {"title": "Invalid monthly task",
                            "scoring_scheme_id": scoring_scheme["id"]}, "schedule": schedule}
    response = client.post(path, headers=auth_headers, json=payload)
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["details"]["issues"][0]["field"] == "schedule_value_json.day"
    assert db.query(Task).count() == task_count
    assert db.query(TaskSchedule).count() == schedule_count
    row = db.get(TaskSchedule, task_schedule["id"])
    assert row.schedule_type == ScheduleType.DAILY
    assert row.schedule_value_json == task_schedule["schedule_value_json"]


@pytest.mark.parametrize("day", [0, 32, True, "31"])
def test_direct_service_rejects_invalid_monthly_dto(db, task, day):
    count = db.query(TaskSchedule).count()
    with pytest.raises(RequestValidationError):
        build_task_schedule_service(db).create_task_schedule(
            task_id=task["id"], user_id=UUID(task["user_id"]),
            payload=CreateTaskScheduleDTO(
                schedule_type=ScheduleType.MONTHLY, schedule_value_json={"day": day},
            ),
        )
    assert db.query(TaskSchedule).count() == count
