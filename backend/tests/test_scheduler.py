from datetime import date, datetime
from unittest.mock import Mock

import pytest

from app import scheduler as scheduler_module
from app.task_instances.commands import GenerateDailyTaskInstancesCommand
from app.task_instances.dependencies import build_generate_task_instances_mediator
from app.task_instances.dtos import GenerateTaskInstancesResultDTO
from app.task_instances.handlers import GenerateDailyTaskInstancesCommandHandler


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
    expected_result = object()

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


def test_generate_daily_task_instances_handler_returns_result_dto():
    generated_instances = [object(), object()]

    class Service:
        def generate_task_instances_for_date(self, target_date):
            assert target_date == date(2026, 10, 7)
            return generated_instances

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
        def generate_task_instances_for_date(self, target_date):
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
        def generate_task_instances_for_date(self, target_date):
            return []

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
