"""Exercise player-local dates at real API and database boundaries."""
from datetime import date, datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.goals.models import Goal
from app.point_ledgers.models import PointLedger
from app.task_instances.models import TaskInstance
from app.task_instances.commands import GenerateDailyTaskInstancesCommand
from app.task_instances.dependencies import build_generate_task_instances_mediator
from app.task_schedules.models import TaskSchedule
from app.tasks.models import Task
from app.users.models import User


def clock(monkeypatch, instant):
    from app.shared import dates
    monkeypatch.setattr(dates, 'utc_now', lambda: datetime.fromisoformat(instant))


@pytest.mark.parametrize('year,month,first,last,outside', [
    (2026, 11, '2026-11-01', '2026-11-30', ['2026-10-31', '2026-12-01']),
    (2024, 2, '2024-02-01', '2024-02-29', ['2024-01-31', '2024-03-01']),
    (2026, 12, '2026-12-01', '2026-12-31', ['2026-11-30', '2027-01-01']),
    (9999, 12, '9999-12-01', '9999-12-31', ['9999-11-30']),
])
def test_month_contains_exactly_its_dates(client, db, ownership_case, year, month, first, last, outside):
    actor = ownership_case['owner']
    for value in [first, last, *outside]:
        db.add(TaskInstance(user_id=actor['user'].id, task_id=actor['rows']['tasks'].id,
                           task_schedule_id=actor['rows']['task_schedules'].id,
                           date_instance=date.fromisoformat(value), scoring_snapshot_json={'normal': 5}))
    db.commit()
    response = client.get('/task_instances/month', headers=actor['headers'], params={'year': year, 'month': month})
    assert response.status_code == 200, response.text
    assert [row['date_instance'] for row in response.json()] == [first, last]


@pytest.mark.parametrize('year,month', [(2026, 0), (2026, 13), (0, 1), (10000, 12)])
def test_invalid_calendar_query_is_validation_error(client, ownership_case, year, month):
    response = client.get('/task_instances/month', headers=ownership_case['owner']['headers'],
                          params={'year': year, 'month': month})
    assert response.status_code == 422


def set_zone(db, actor, name):
    db.get(User, actor['user'].id).timezone = name
    db.commit()


@pytest.mark.parametrize('zone,instant,expected', [
    ('Asia/Kuala_Lumpur', '2026-12-31T16:05:00+00:00', '2027-01-01'),
    ('America/Los_Angeles', '2026-12-31T16:05:00+00:00', '2026-12-31'),
    ('Asia/Kathmandu', '2026-12-31T18:20:00+00:00', '2027-01-01'),
    ('America/Los_Angeles', '2027-03-14T07:30:00+00:00', '2027-03-13'),
    ('America/Los_Angeles', '2027-03-14T10:30:00+00:00', '2027-03-14'),
])
def test_new_goal_workflow_and_ledger_use_players_day(client, db, ownership_case, monkeypatch, zone, instant, expected):
    clock(monkeypatch, instant)
    actor = ownership_case['owner']
    set_zone(db, actor, zone)
    actor['rows']['task_instances'].date_instance = date.fromisoformat(expected)
    db.commit()
    goal = client.post('/goals', headers=actor['headers'], json={'title': 'Local goal'})
    assert goal.status_code == 201, goal.text
    assert goal.json()['start_date'] == expected
    response = client.post('/workflows/tasks', headers=actor['headers'], json={
        'task': {'title': 'Local daily todo'},
        'schedule': {'schedule_type': 'daily', 'schedule_value_json': {}},
    })
    assert response.status_code == 201, response.text
    task_id = response.json()['task']['id']
    with Session(db.get_bind()) as reader:
        row = reader.query(TaskInstance).filter_by(task_id=task_id).one()
        assert row.date_instance.isoformat() == expected
    result = client.post(f"/task_instances/{actor['rows']['task_instances'].id}/complete",
                         headers=actor['headers'], json={'completion_level': 'normal'})
    assert result.status_code == 200, result.text
    assert result.json()['progress']['today'] == expected
    assert result.json()['point_ledger']['event_at'] == expected


def test_ai_confirmation_uses_one_local_day_and_preserves_explicit_dates(client, db, ownership_case, monkeypatch):
    from ai_draft_support import save_draft
    clock(monkeypatch, '2026-12-31T16:05:00+00:00')
    actor = ownership_case['owner']
    set_zone(db, actor, 'Asia/Kuala_Lumpur')
    from app.goals.service import GoalService
    original = GoalService.create_goal
    def cross_midnight(self, user_id, payload):
        goal = original(self, user_id, payload)
        clock(monkeypatch, '2027-01-01T16:05:00+00:00')
        return goal
    monkeypatch.setattr(GoalService, 'create_goal', cross_midnight)
    draft_id = save_draft(db, actor['user'].id, {'goal_title': 'New year plan', 'tasks': [
        {'title': title, 'scoring_scheme_id': actor['rows']['scoring_schemes'].id,
         'schedule_type': 'daily', 'schedule_value_json': {}} for title in ['Read', 'Walk']
    ]})
    response = client.post('/workflows/ai/confirm', headers=actor['headers'], json={'draft_id': draft_id})
    assert response.status_code == 201, response.text
    assert response.json()['goal']['start_date'] == '2027-01-01'
    assert {item['schedule']['start_date'] for item in response.json()['task_with_schedule_list']} == {'2027-01-01'}
    explicit = client.post('/workflows/tasks', headers=actor['headers'], json={
        'task': {'title': 'Chosen day'}, 'schedule': {'schedule_type': 'once', 'schedule_value_json': {},
                                                    'start_date': '2030-02-10'},
    })
    assert explicit.status_code == 201
    assert explicit.json()['task_instance']['date_instance'] == '2030-02-10'


def test_scheduled_pass_generates_each_players_today_without_duplicates(db, ownership_case, monkeypatch):
    clock(monkeypatch, '2026-12-31T16:05:00+00:00')
    owner, other = ownership_case['owner'], ownership_case['other']
    set_zone(db, owner, 'Asia/Kuala_Lumpur')
    set_zone(db, other, 'America/Los_Angeles')
    player_ids = {owner['user'].id, other['user'].id}
    db.query(TaskInstance).filter(TaskInstance.user_id.in_(player_ids)).delete(synchronize_session=False)
    db.commit()
    mediator = build_generate_task_instances_mediator(db)
    command = GenerateDailyTaskInstancesCommand(target_date=None)
    first = mediator.send(command)
    # The batch also processes schedules from other tests in a full-suite run.
    # Assert precisely on this fixture's players rather than global DB counts.
    assert first.created_count >= 2
    assert {(str(row.user_id), row.date_instance) for row in first.task_instances if row.user_id in player_ids} == {
        (str(owner['user'].id), date(2027, 1, 1)), (str(other['user'].id), date(2026, 12, 31)),
    }
    assert mediator.send(command).created_count == 0


def test_invalid_timezone_rolls_back_goal_creation(client, db, ownership_case):
    actor = ownership_case['owner']
    set_zone(db, actor, 'invalid/legacy-zone')
    before = db.query(Goal).count()
    response = client.post('/goals', headers=actor['headers'], json={'title': 'Invalid zone goal'})
    assert response.status_code == 422, response.text
    assert db.query(Goal).count() == before


def test_invalid_legacy_timezone_rolls_back_the_entire_scheduled_pass(db, ownership_case, monkeypatch):
    from app.errors.exception import RequestValidationError
    clock(monkeypatch, '2026-12-31T16:05:00+00:00')
    owner, other = ownership_case['owner'], ownership_case['other']
    set_zone(db, owner, 'Asia/Kuala_Lumpur')
    set_zone(db, other, 'invalid/legacy-zone')
    before_count = db.query(TaskInstance).count()
    with pytest.raises(RequestValidationError):
        build_generate_task_instances_mediator(db).send(GenerateDailyTaskInstancesCommand())
    assert db.query(TaskInstance).count() == before_count


@pytest.mark.asyncio
async def test_scheduler_checks_local_days_once_daily_at_configured_midnight(monkeypatch):
    import asyncio
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from app import scheduler as module
    scheduler = AsyncIOScheduler(timezone='Asia/Kuala_Lumpur')
    monkeypatch.setattr(module, 'scheduler', scheduler)
    monkeypatch.setattr(module, 'SCHEDULER_ENABLED', True)
    monkeypatch.setattr(module, 'run_generate_task_instances_for_today', lambda: None)
    before_start = datetime.now(timezone.utc)
    try:
        module.start_scheduler()
        job = scheduler.get_job('generate_task_instances_daily')
        first = job.trigger.get_next_fire_time(None, datetime(2027, 1, 1, 15, 59, tzinfo=timezone.utc))
        assert first == datetime(2027, 1, 1, 16, 0, tzinfo=timezone.utc)
        second = job.trigger.get_next_fire_time(first, first)
        assert second == datetime(2027, 1, 2, 16, 0, tzinfo=timezone.utc)
        # Actual startup must schedule the next configured midnight, not run now.
        assert job.next_run_time > before_start
        local_next = job.next_run_time.astimezone(scheduler.timezone)
        assert (local_next.hour, local_next.minute, local_next.second, local_next.microsecond) == (0, 0, 0, 0)
        assert job.max_instances == 1 and job.coalesce
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)
            await asyncio.sleep(0)


def test_one_completion_uses_one_instant_when_the_clock_crosses_midnight(client, db, ownership_case, monkeypatch):
    from app.shared import dates
    from app.progress.models import TaskCompletion
    actor = ownership_case['owner']
    set_zone(db, actor, 'Asia/Kuala_Lumpur')
    before = datetime.fromisoformat('2026-12-31T15:59:59.999000+00:00')
    after = datetime.fromisoformat('2026-12-31T16:00:00+00:00')
    reads = []
    def crossing_clock():
        reads.append(True)
        return before if len(reads) == 1 else after
    monkeypatch.setattr(dates, 'utc_now', crossing_clock)
    response = client.post(f"/task_instances/{actor['rows']['task_instances'].id}/complete",
                           headers=actor['headers'], json={'completion_level': 'normal'})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['point_ledger']['event_at'] == result['progress']['today'] == '2026-12-31'
    with Session(db.get_bind()) as reader:
        fact = reader.query(TaskCompletion).filter_by(user_id=actor['user'].id).one()
        assert fact.completed_local_date == date(2026, 12, 31) and fact.completed_at == before
