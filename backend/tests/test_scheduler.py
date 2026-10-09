from datetime import date, datetime
import logging
from unittest.mock import Mock

import pytest

from app import scheduler as scheduler_module
from app.task_instances.commands import GenerateDailyTaskInstancesCommand
from app.task_instances.dependencies import build_generate_task_instances_mediator, build_task_instance_service
from app.task_instances.dtos import GenerateTaskInstancesResultDTO
from app.task_instances.handlers import GenerateDailyTaskInstancesCommandHandler
from app.core.behaviors import get_request_id
from app.task_instances.models import TaskInstance
from app.task_instances.repository import TaskInstanceRepository
from app.task_schedules.repository import TaskScheduleRepository
from app.task_schedules.models import TaskSchedule
from app.shared.enums import ScheduleType


class FakeSession:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


class FixedDateTime:
    @classmethod
    def now(cls, timezone):
        return datetime(2026, 10, 7, 0, 5, tzinfo=timezone)


def test_daily_generation_job_sends_command_and_closes_session(monkeypatch):
    session = FakeSession()
    sent_requests = []
    expected_result = GenerateTaskInstancesResultDTO(
        target_date=date(2026, 10, 7), task_instances=(),
        processed_count=3, created_count=0,
    )

    class Mediator:
        def send(self, request):
            sent_requests.append(request)
            return expected_result

    monkeypatch.setattr(scheduler_module, "SessionLocal", lambda: session)
    monkeypatch.setattr(scheduler_module, "datetime", FixedDateTime)
    monkeypatch.setattr(
        scheduler_module,
        "build_generate_task_instances_mediator",
        lambda db: Mediator(),
    )

    result = scheduler_module.run_generate_task_instances_for_today()

    assert result is expected_result
    assert len(sent_requests) == 1
    assert isinstance(sent_requests[0], GenerateDailyTaskInstancesCommand)
    assert sent_requests[0].target_date == date(2026, 10, 7)
    assert session.commits == 0
    assert session.rollbacks == 0
    assert session.closed is True


def test_scheduler_logs_committed_counts_with_cqrs_request_id(
    monkeypatch, caplog,
):
    session = FakeSession()

    class Service:
        def generate_task_instances_with_summary(self, target_date):
            return GenerateTaskInstancesResultDTO(
                target_date=target_date, task_instances=(),
                processed_count=3, created_count=0,
            )

    monkeypatch.setattr(scheduler_module, "SessionLocal", lambda: session)
    monkeypatch.setattr(scheduler_module, "datetime", FixedDateTime)
    monkeypatch.setattr(
        "app.task_instances.dependencies.build_task_instance_service",
        lambda db: Service(),
    )
    with caplog.at_level(logging.INFO):
        scheduler_module.run_generate_task_instances_for_today()

    success = next(r for r in caplog.records if r.msg == "scheduler_generation_completed")
    cqrs = next(r for r in caplog.records if r.msg == "cqrs_request_completed")
    assert success.request_id == cqrs.request_id
    assert success.processed_count == 3
    assert success.created_count == 0
    assert success.target_date == "2026-10-07"
    assert session.commits == 1
    assert session.closed
    assert get_request_id() is None


def test_generation_summary_counts_only_new_rows(db, task_schedule):
    mediator = build_generate_task_instances_mediator(db)
    command = GenerateDailyTaskInstancesCommand(target_date=date(2035, 1, 10))
    first = mediator.send(command)
    second = mediator.send(command)
    assert first.created_count >= 1
    assert first.processed_count >= 1
    assert second.created_count == 0
    assert second.processed_count == first.processed_count
    assert len(second.task_instances) == len(first.task_instances)


def test_inactive_task_stays_manageable_and_generation_resumes_without_duplicates(
    client, auth_headers, db, task, task_schedule, task_instance,
):
    assert client.post(
        f"/tasks/{task['id']}", headers=auth_headers, json={"is_active": False},
    ).status_code == 200
    assert client.get(f"/tasks/{task['id']}", headers=auth_headers).status_code == 200
    assert task_schedule["id"] in {
        row["id"] for row in client.get("/task_schedules", headers=auth_headers).json()
    }
    assert TaskScheduleRepository(db).get_by_id(task_schedule["id"]) is not None

    mediator = build_generate_task_instances_mediator(db)
    command = GenerateDailyTaskInstancesCommand(target_date=date(2041, 7, 10))
    disabled = mediator.send(command)
    assert task["id"] not in {row.task_id for row in disabled.task_instances}
    assert db.query(TaskInstance).filter(
        TaskInstance.task_id == task["id"], TaskInstance.date_instance == command.target_date,
    ).count() == 0
    assert db.get(TaskInstance, task_instance["id"]) is not None

    assert client.post(
        f"/tasks/{task['id']}", headers=auth_headers, json={"is_active": True},
    ).status_code == 200
    enabled = mediator.send(command)
    instance = next(row for row in enabled.task_instances if row.task_id == task["id"])
    assert enabled.processed_count == disabled.processed_count + 1
    assert enabled.created_count == 1
    repeated = mediator.send(command)
    assert repeated.created_count == 0
    assert next(row.id for row in repeated.task_instances if row.task_id == task["id"]) == instance.id
    assert db.query(TaskInstance).filter(
        TaskInstance.task_id == task["id"], TaskInstance.date_instance == command.target_date,
    ).count() == 1


def test_generate_endpoint_skips_inactive_tasks(client, auth_headers, db, task, task_schedule):
    assert client.post(
        f"/tasks/{task['id']}", headers=auth_headers, json={"is_active": False},
    ).status_code == 200
    response = client.post(
        "/tasks_instances/generate", headers=auth_headers,
        json={"date_instance": "2041-07-11"},
    )
    assert response.status_code == 201
    assert task["id"] not in {row["task_id"] for row in response.json()}
    assert db.query(TaskInstance).filter(
        TaskInstance.task_id == task["id"], TaskInstance.date_instance == date(2041, 7, 11),
    ).count() == 0


@pytest.mark.parametrize("days,target_date,expected", [
    ([0, 6], date(2026, 10, 5), True),
    ([0, 6], date(2026, 10, 6), False),
    ([0, 6], date(2026, 10, 7), False),
    ([0, 6], date(2026, 10, 8), False),
    ([0, 6], date(2026, 10, 9), False),
    ([0, 6], date(2026, 10, 10), False),
    ([0, 6], date(2026, 10, 11), True),
    ([0, 6], date(2026, 10, 12), True),
    ([0], date(2026, 10, 11), False),
    ([6], date(2026, 10, 5), False),
    ([], date(2026, 10, 5), False),
])
def test_weekly_generation_matches_selected_weekdays(db, days, target_date, expected):
    schedule = TaskSchedule(
        schedule_type=ScheduleType.WEEKLY, schedule_value_json={"days": days},
        start_date=None, end_date=None,
    )
    assert build_task_instance_service(db)._should_generate_for_date(schedule, target_date) is expected


@pytest.mark.parametrize("schedule_type,value", [
    (ScheduleType.DAILY, {}),
    (ScheduleType.WEEKLY, {"days": [0]}),
    (ScheduleType.MONTHLY, {"day": 5}),
])
@pytest.mark.parametrize("start_date,end_date,expected", [
    (None, None, True),
    (date(2026, 10, 6), None, False),
    (date(2026, 10, 5), None, True),
    (None, date(2026, 10, 4), False),
    (None, date(2026, 10, 5), True),
    (date(2026, 10, 5), date(2026, 10, 5), True),
])
def test_generation_date_range_is_inclusive(
    db, schedule_type, value, start_date, end_date, expected,
):
    schedule = TaskSchedule(
        schedule_type=schedule_type, schedule_value_json=value,
        start_date=start_date, end_date=end_date,
    )
    assert build_task_instance_service(db)._should_generate_for_date(schedule, date(2026, 10, 5)) is expected


@pytest.mark.parametrize("schedule_type,value,end_date,dates,expected_dates", [
    ("daily", {}, "2027-01-01",
     [date(2026, 12, 30), date(2026, 12, 31), date(2027, 1, 1), date(2027, 1, 2)],
     [date(2026, 12, 31), date(2027, 1, 1)]),
    ("weekly", {"days": [3, 4]}, "2027-01-01",
     [date(2026, 12, 24), date(2026, 12, 31), date(2027, 1, 1), date(2027, 1, 7)],
     [date(2026, 12, 31), date(2027, 1, 1)]),
    ("monthly", {"day": 31}, "2027-01-31",
     [date(2026, 10, 31), date(2026, 12, 31), date(2027, 1, 1), date(2027, 1, 31), date(2027, 3, 31)],
     [date(2026, 12, 31), date(2027, 1, 31)]),
])
def test_generation_persists_only_eligible_dates_across_year_boundary(
    client, auth_headers, db, task, task_schedule,
    schedule_type, value, end_date, dates, expected_dates,
):
    response = client.post(
        f"/task_schedules/{task_schedule['id']}", headers=auth_headers,
        json={"schedule_type": schedule_type, "schedule_value_json": value,
              "start_date": "2026-12-31", "end_date": end_date},
    )
    assert response.status_code == 200
    mediator = build_generate_task_instances_mediator(db)
    for target_date in dates:
        result = mediator.send(GenerateDailyTaskInstancesCommand(target_date=target_date))
        instances = [row for row in result.task_instances if row.task_id == task["id"]]
        if target_date in expected_dates:
            assert len(instances) == 1
            assert instances[0].date_instance == target_date
        else:
            assert instances == []

    repeated = mediator.send(GenerateDailyTaskInstancesCommand(target_date=expected_dates[-1]))
    assert repeated.created_count == 0
    stored_dates = [row.date_instance for row in db.query(TaskInstance).filter(
        TaskInstance.task_id == task["id"],
    ).order_by(TaskInstance.date_instance).all()]
    assert stored_dates == expected_dates


@pytest.mark.parametrize("failure_stage", ["insert", "commit"])
def test_scheduler_failure_rolls_back_flushed_rows_and_logs(
    db, task_schedule, monkeypatch, caplog, failure_stage,
):
    target_date = date(2035, 2, 10)
    original_create = TaskInstanceRepository.create

    def fail_after_flush(repo, instance):
        original_create(repo, instance)
        raise RuntimeError("failure after insert")

    def fail_commit():
        raise RuntimeError("failure during commit")

    class FailureDateTime:
        @classmethod
        def now(cls, timezone):
            return datetime(2035, 2, 10, tzinfo=timezone)

    monkeypatch.setattr(scheduler_module, "SessionLocal", lambda: db)
    monkeypatch.setattr(scheduler_module, "datetime", FailureDateTime)
    if failure_stage == "insert":
        monkeypatch.setattr(TaskInstanceRepository, "create", fail_after_flush)
    else:
        monkeypatch.setattr(db, "commit", fail_commit)
    close = Mock(wraps=db.close)
    monkeypatch.setattr(db, "close", close)

    with caplog.at_level(logging.INFO), pytest.raises(RuntimeError, match="failure"):
        scheduler_module.run_generate_task_instances_for_today()

    failure = next(r for r in caplog.records if r.msg == "scheduler_generation_failed")
    cqrs = next(r for r in caplog.records if r.msg == "cqrs_request_failed")
    assert failure.request_id == cqrs.request_id
    assert failure.target_date == target_date.isoformat()
    assert failure.outcome == "failure"
    assert failure.created_count is None
    assert failure.processed_count is None
    assert failure.exc_info[0] is RuntimeError
    assert not any(r.msg == "scheduler_generation_completed" for r in caplog.records)
    close.assert_called_once()
    assert not db.in_transaction()
    assert db.query(TaskInstance).filter(TaskInstance.date_instance == target_date).count() == 0
    assert get_request_id() is None


def test_generate_daily_task_instances_handler_returns_result_dto():
    generated_instances = [object(), object()]

    class Service:
        def generate_task_instances_with_summary(self, target_date):
            assert target_date == date(2026, 10, 7)
            return GenerateTaskInstancesResultDTO(
                target_date=target_date, task_instances=tuple(generated_instances),
                processed_count=3, created_count=2,
            )

    result = GenerateDailyTaskInstancesCommandHandler(Service()).handle(
        GenerateDailyTaskInstancesCommand(target_date=date(2026, 10, 7))
    )

    assert isinstance(result, GenerateTaskInstancesResultDTO)
    assert result.target_date == date(2026, 10, 7)
    assert result.task_instances == tuple(generated_instances)
    assert result.created_count == 2


def test_generate_daily_task_instances_mediator_rolls_back_on_failure(
    monkeypatch,
):
    class FailingService:
        def generate_task_instances_with_summary(self, target_date):
            raise RuntimeError("generation failed")

    monkeypatch.setattr(
        "app.task_instances.dependencies.build_task_instance_service",
        lambda db: FailingService(),
    )
    session = FakeSession()
    mediator = build_generate_task_instances_mediator(session)

    with pytest.raises(RuntimeError, match="generation failed"):
        mediator.send(GenerateDailyTaskInstancesCommand(
            target_date=date(2026, 10, 7),
        ))

    assert session.commits == 0
    assert session.rollbacks == 1


def test_generate_daily_task_instances_mediator_commits_on_success(
    monkeypatch,
):
    class Service:
        def generate_task_instances_with_summary(self, target_date):
            return GenerateTaskInstancesResultDTO(
                target_date=target_date, task_instances=(),
                processed_count=0, created_count=0,
            )

    monkeypatch.setattr(
        "app.task_instances.dependencies.build_task_instance_service",
        lambda db: Service(),
    )
    session = FakeSession()
    mediator = build_generate_task_instances_mediator(session)

    result = mediator.send(GenerateDailyTaskInstancesCommand(
        target_date=date(2026, 10, 7),
    ))

    assert result.created_count == 0
    assert session.commits == 1
    assert session.rollbacks == 0


def test_start_scheduler_does_nothing_when_disabled(monkeypatch):
    add_job_mock = Mock()
    start_mock = Mock()

    monkeypatch.setattr(
        scheduler_module,
        "SCHEDULER_ENABLED",
        False,
    )
    monkeypatch.setattr(
        scheduler_module.scheduler,
        "add_job",
        add_job_mock,
    )
    monkeypatch.setattr(
        scheduler_module.scheduler,
        "start",
        start_mock,
    )

    scheduler_module.start_scheduler()

    add_job_mock.assert_not_called()
    start_mock.assert_not_called()
