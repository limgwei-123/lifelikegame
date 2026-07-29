from unittest.mock import Mock

from app import scheduler as scheduler_module


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