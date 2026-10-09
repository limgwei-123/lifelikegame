from datetime import date, datetime
import logging
from unittest.mock import Mock

import pytest

from app import scheduler as scheduler_module
from app.task_instances.commands import GenerateDailyTaskInstancesCommand
from app.task_instances.dependencies import build_generate_task_instances_mediator
from app.task_instances.dtos import GenerateTaskInstancesResultDTO
from app.task_instances.handlers import GenerateDailyTaskInstancesCommandHandler
from app.core.behaviors import get_request_id
from app.task_instances.models import TaskInstance
from app.task_instances.repository import TaskInstanceRepository


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
