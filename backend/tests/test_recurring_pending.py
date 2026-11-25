from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.auth.security import create_access_token
from app.task_instances.models import TaskInstance
from app.task_instances.commands import CompleteTaskInstanceCommand
from app.task_instances.dependencies import build_complete_task_instance_mediator
from app.tasks.models import Task
from app.users.models import User


@pytest.fixture
def actor(client, db, monkeypatch):
    from app.shared import dates
    now = [datetime.fromisoformat('2026-11-25T04:00:00+00:00')]
    monkeypatch.setattr(dates, 'utc_now', lambda: now[0])
    user = User(email=f'recurring-{uuid4()}@example.com', password_hash='unused', timezone='Asia/Kuala_Lumpur')
    db.add(user)
    db.commit()
    user_id = user.id
    result = {'id': user_id, 'headers': {'Authorization': f'Bearer {create_access_token(str(user_id))}'}, 'now': now}
    yield result
    db.rollback()
    db.query(User).filter(User.id == user_id).delete()
    db.commit()


def create(client, actor, kind='daily', value=None, start='2026-11-25', end=None):
    response = client.post('/workflows/tasks', headers=actor['headers'], json={
        'task': {'title': 'Recurring todo'}, 'schedule': {'schedule_type': kind, 'schedule_value_json': value or {},
        'start_date': start, 'end_date': end},
    })
    assert response.status_code == 201, response.text
    assert response.json()['task_instance'] is not None
    return response.json()


def complete(client, actor, instance_id):
    return client.post(f'/task_instances/{instance_id}/complete', headers=actor['headers'], json={})


def test_daily_completion_creates_tomorrow_once_and_blocks_early_completion(client, db, actor):
    workflow = create(client, actor)
    current = workflow['task_instance']
    result = complete(client, actor, current['id'])
    assert result.status_code == 200, result.text
    future = result.json()['next_task_instance']
    assert future['date_instance'] == '2026-11-26' and future['status'] == 'todo'
    assert complete(client, actor, current['id']).json()['next_task_instance']['id'] == future['id']
    assert complete(client, actor, future['id']).status_code == 422
    assert db.query(TaskInstance).filter_by(task_id=workflow['task']['id']).count() == 2
    actor['now'][0] = datetime.fromisoformat('2026-11-26T04:00:00+00:00')
    assert complete(client, actor, future['id']).json()['next_task_instance']['date_instance'] == '2026-11-27'


def test_overdue_does_not_stack_and_completes_on_actual_day(client, db, actor):
    workflow = create(client, actor)
    current = workflow['task_instance']
    actor['now'][0] = datetime.fromisoformat('2026-11-28T04:00:00+00:00')
    for target in ('2026-11-26', '2026-11-27', '2026-11-28'):
        response = client.post('/tasks_instances/generate', headers=actor['headers'], json={'date_instance': target})
        assert response.status_code == 201, response.text
    pending = client.get('/task_instances/pending', headers=actor['headers'])
    assert pending.status_code == 200
    assert [item['id'] for item in pending.json()] == [current['id']]
    result = complete(client, actor, current['id']).json()
    assert result['progress']['today'] == '2026-11-28' and result['progress']['current_streak'] == 1
    assert result['next_task_instance']['date_instance'] == '2026-11-29'
    assert db.query(TaskInstance).filter_by(task_id=workflow['task']['id']).count() == 2


@pytest.mark.parametrize('kind,value,start,completion,next_date', [
    ('weekly', {'days': [0]}, '2026-11-23', '2026-11-25', '2026-11-30'),
    ('weekly', {'days': [0, 2, 4]}, '2026-11-25', '2026-11-25', '2026-11-27'),
    ('monthly', {'day': 31}, '2026-10-31', '2026-11-25', '2026-12-31'),
    ('monthly', {'day': 29}, '2028-01-29', '2028-01-29', '2028-02-29'),
    ('monthly', {'day': 29}, '2027-01-29', '2027-01-29', '2027-03-29'),
])
def test_fixed_calendar_advancement(client, actor, kind, value, start, completion, next_date):
    actor['now'][0] = datetime.fromisoformat(start + 'T04:00:00+00:00')
    workflow = create(client, actor, kind, value, start)
    actor['now'][0] = datetime.fromisoformat(completion + 'T04:00:00+00:00')
    result = complete(client, actor, workflow['task_instance']['id'])
    assert result.status_code == 200, result.text
    assert result.json()['next_task_instance']['date_instance'] == next_date


@pytest.mark.parametrize('stop', ['end', 'inactive', 'delete_schedule'])
def test_finishing_existing_work_after_stop_does_not_create_another(client, actor, stop):
    workflow = create(client, actor, end='2026-11-25' if stop == 'end' else None)
    if stop == 'inactive':
        assert client.post(f"/tasks/{workflow['task']['id']}", headers=actor['headers'], json={'is_active': False}).status_code == 200
    if stop == 'delete_schedule':
        assert client.post(f"/task_schedules/{workflow['schedule']['id']}/delete", headers=actor['headers']).status_code == 204
    result = complete(client, actor, workflow['task_instance']['id'])
    assert result.status_code == 200, result.text
    assert result.json()['next_task_instance'] is None


def test_next_occurrence_failure_rolls_back_completion_and_progress(client, db, actor, monkeypatch):
    from app.task_instances.repository import TaskInstanceRepository
    workflow = create(client, actor)
    original = TaskInstanceRepository.create
    def fail_after_flush(self, instance):
        original(self, instance)
        raise RuntimeError('next occurrence failed')
    monkeypatch.setattr(TaskInstanceRepository, 'create', fail_after_flush)
    with pytest.raises(RuntimeError, match='next occurrence failed'):
        complete(client, actor, workflow['task_instance']['id'])
    with Session(db.get_bind()) as reader:
        rows = reader.query(TaskInstance).filter_by(task_id=workflow['task']['id']).all()
        assert len(rows) == 1 and rows[0].status == 'todo'
    assert client.get('/progress', headers=actor['headers']).json()['total_completed'] == 0


def test_manual_creation_cannot_add_a_second_current_occurrence(client, actor):
    workflow = create(client, actor)
    response = client.post(f"/tasks/{workflow['task']['id']}/task_schedules/{workflow['schedule']['id']}/task_instances",
        headers=actor['headers'], json={'date_instance': '2026-11-30'})
    assert response.status_code == 409


def test_concurrent_completion_advances_once(client, db, actor):
    workflow = create(client, actor)
    ready = Barrier(2)
    def worker():
        with Session(db.get_bind()) as session:
            ready.wait(timeout=10)
            result = build_complete_task_instance_mediator(session).send(CompleteTaskInstanceCommand(
                user_id=actor['id'], task_instance_id=workflow['task_instance']['id']))
            return result.next_task_instance.id
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker) for _ in range(2)]
        ids = [future.result(timeout=20) for future in futures]
    assert ids[0] == ids[1]
    with Session(db.get_bind()) as reader:
        assert reader.query(TaskInstance).filter_by(task_id=workflow['task']['id']).count() == 2


def test_manual_endpoint_cannot_recreate_past_cycles_after_schedule_ends(client, actor):
    actor['now'][0] = datetime.fromisoformat('2026-11-24T04:00:00+00:00')
    workflow = create(client, actor, start='2026-11-24', end='2026-11-25')
    actor['now'][0] = datetime.fromisoformat('2026-11-25T04:00:00+00:00')
    assert complete(client, actor, workflow['task_instance']['id']).json()['next_task_instance'] is None
    response = client.post(f"/tasks/{workflow['task']['id']}/task_schedules/{workflow['schedule']['id']}/task_instances",
        headers=actor['headers'], json={'date_instance': '2026-11-25'})
    assert response.status_code == 409


def test_legacy_extra_rows_are_preserved_but_not_resurrected(client, db, actor):
    from app.task_schedules.models import TaskSchedule
    task = Task(user_id=actor['id'], goal_id=None, title='Legacy todo')
    db.add(task)
    db.flush()
    schedule = TaskSchedule(user_id=actor['id'], task_id=task.id, schedule_type='daily',
                            schedule_value_json={}, start_date=date(2026, 11, 20))
    db.add(schedule)
    db.flush()
    rows = [TaskInstance(user_id=actor['id'], task_id=task.id, task_schedule_id=schedule.id,
                        date_instance=date(2026, 11, day)) for day in (20, 21, 22)]
    db.add_all(rows)
    db.commit()
    ids, task_id = [row.id for row in rows], task.id
    assert [row['id'] for row in client.get('/task_instances/pending', headers=actor['headers']).json()] == [ids[0]]
    result = complete(client, actor, ids[0])
    assert result.status_code == 200, result.text
    assert result.json()['next_task_instance']['date_instance'] == '2026-11-26'
    assert client.get('/task_instances/pending', headers=actor['headers']).json() == []
    assert complete(client, actor, ids[1]).status_code == 409
    with Session(db.get_bind()) as reader:
        assert reader.query(TaskInstance).filter(TaskInstance.id.in_(ids[1:]), TaskInstance.status == 'todo').count() == 2
        assert reader.query(TaskInstance).filter_by(task_id=task_id).count() == 4


def test_current_pending_endpoint_requires_auth_and_filters_ownership(client, actor, ownership_case):
    workflow = create(client, actor)
    assert client.get('/task_instances/pending').status_code == 401
    assert workflow['task_instance']['id'] not in {row['id'] for row in
        client.get('/task_instances/pending', headers=ownership_case['other']['headers']).json()}


def test_once_task_does_not_recur(client, actor):
    workflow = create(client, actor, kind='once')
    response = complete(client, actor, workflow['task_instance']['id'])
    assert response.status_code == 200 and response.json()['next_task_instance'] is None


def test_last_supported_calendar_day_does_not_overflow(client, actor):
    actor['now'][0] = datetime.fromisoformat('9999-12-31T04:00:00+00:00')
    workflow = create(client, actor, start='9999-12-31')
    response = complete(client, actor, workflow['task_instance']['id'])
    assert response.status_code == 200 and response.json()['next_task_instance'] is None


def test_pending_selection_does_not_leak_inconsistent_foreign_owned_rows(client, db, actor, ownership_case):
    workflow = create(client, actor)
    db.add(TaskInstance(user_id=ownership_case['other']['user'].id, task_id=workflow['task']['id'],
                        task_schedule_id=workflow['schedule']['id'], date_instance=date(2026, 11, 24),
                        generated_reason='recurring'))
    db.commit()
    pending = client.get('/task_instances/pending', headers=actor['headers'])
    assert pending.status_code == 200
    assert [row['id'] for row in pending.json()] == [workflow['task_instance']['id']]
    assert all(row['user_id'] == str(actor['id']) for row in pending.json())


def test_scored_recurrence_keeps_single_points_and_boss_award(client, db, actor):
    goal = client.post('/goals', headers=actor['headers'], json={'title': 'Exercise'}).json()
    scheme = client.post('/scoring_schemes', headers=actor['headers'], json={'title': 'Effort', 'levels_json': {'done': 3}}).json()
    response = client.post('/workflows/tasks', headers=actor['headers'], json={
        'goal_id': goal['id'], 'task': {'title': 'Walk', 'scoring_scheme_id': scheme['id']},
        'schedule': {'schedule_type': 'daily', 'schedule_value_json': {}, 'start_date': '2026-11-25'},
    })
    assert response.status_code == 201, response.text
    row = response.json()['task_instance']
    first = complete(client, actor, row['id'])
    assert first.status_code == 200, first.text
    assert first.json()['user']['current_value'] == 3
    assert first.json()['progress']['total_damage'] == 1
    assert first.json()['next_task_instance']['scoring_snapshot_json'] == {'done': 3}
    again = complete(client, actor, row['id'])
    assert again.status_code == 200 and again.json()['user']['current_value'] == 3
    assert again.json()['progress']['total_damage'] == 1


def test_changing_schedule_type_cannot_complete_managed_future_early(client, actor):
    workflow = create(client, actor)
    future = complete(client, actor, workflow['task_instance']['id']).json()['next_task_instance']
    assert client.post(f"/task_schedules/{workflow['schedule']['id']}", headers=actor['headers'],
                       json={'schedule_type': 'once', 'schedule_value_json': {}}).status_code == 200
    assert complete(client, actor, future['id']).status_code == 422
    assert client.post(f"/tasks/{workflow['task']['id']}/task_schedules/{workflow['schedule']['id']}/task_instances",
                       headers=actor['headers'], json={'date_instance': '2026-11-25'}).status_code == 409


def test_replacing_schedule_preserves_unfinished_current_work(client, actor):
    workflow = create(client, actor)
    assert client.post(f"/task_schedules/{workflow['schedule']['id']}/delete", headers=actor['headers']).status_code == 204
    replacement = client.post(f"/tasks/{workflow['task']['id']}/task_schedules", headers=actor['headers'],
                              json={'schedule_type': 'daily', 'schedule_value_json': {}, 'start_date': '2026-11-26'})
    assert replacement.status_code == 201, replacement.text
    actor['now'][0] = datetime.fromisoformat('2026-11-26T04:00:00+00:00')
    generated = client.post('/tasks_instances/generate', headers=actor['headers'], json={'date_instance': '2026-11-26'})
    assert generated.status_code == 201
    assert [row['id'] for row in generated.json()] == [workflow['task_instance']['id']]
    assert [row['id'] for row in client.get('/task_instances/pending', headers=actor['headers']).json()] == [workflow['task_instance']['id']]
    result = complete(client, actor, workflow['task_instance']['id'])
    assert result.status_code == 200, result.text
    assert result.json()['next_task_instance']['task_schedule_id'] == replacement.json()['id']
    assert result.json()['next_task_instance']['date_instance'] == '2026-11-27'


def test_legacy_row_on_exact_next_future_date_is_reused_without_duplicate(client, db, actor):
    workflow = create(client, actor)
    legacy = TaskInstance(user_id=actor['id'], task_id=workflow['task']['id'], task_schedule_id=workflow['schedule']['id'],
                          date_instance=date(2026, 11, 26))
    db.add(legacy)
    db.commit()
    legacy_id = legacy.id
    response = complete(client, actor, workflow['task_instance']['id'])
    assert response.status_code == 200, response.text
    assert response.json()['next_task_instance']['id'] == legacy_id
    assert complete(client, actor, legacy_id).status_code == 422


def test_generation_and_completion_for_same_user_have_consistent_lock_order(client, db, actor, monkeypatch):
    from threading import Event, current_thread
    from app.core.unit_of_work import build_unit_of_work
    from app.task_instances.repository import TaskInstanceRepository
    from app.task_instances.dependencies import build_task_instance_service
    from app.users.repository import UserRepository
    task = client.post('/tasks', headers=actor['headers'], json={'title': 'Earlier task'}).json()
    schedule = client.post(f"/tasks/{task['id']}/task_schedules", headers=actor['headers'],
                           json={'schedule_type': 'daily', 'schedule_value_json': {}, 'start_date': '2026-11-25'})
    assert schedule.status_code == 201
    workflow = create(client, actor)
    # The workflow initialized both tasks; remove only this fixture's first
    # occurrence so generation must insert it (and take its real FK locks).
    db.query(TaskInstance).filter_by(task_id=task['id']).delete(synchronize_session=False)
    db.commit()
    inserted, completing = Event(), Event()
    original_create = TaskInstanceRepository.create
    original_user_lock = UserRepository.get_by_id_for_update
    def create_row(self, instance):
        row = original_create(self, instance)
        if current_thread().name.startswith('generation') and instance.task_id == task['id']:
            inserted.set()
            assert completing.wait(10)
        return row
    def lock_user(self, user_id):
        if current_thread().name.startswith('completion'):
            completing.set()
        return original_user_lock(self, user_id)
    monkeypatch.setattr(TaskInstanceRepository, 'create', create_row)
    monkeypatch.setattr(UserRepository, 'get_by_id_for_update', lock_user)
    def generate():
        with Session(db.get_bind()) as session:
            with build_unit_of_work(session).begin():
                return len(build_task_instance_service(session).generate_task_instances_for_user(date(2026, 11, 25), actor['id']))
    def finish():
        assert inserted.wait(10)
        with Session(db.get_bind()) as session:
            return build_complete_task_instance_mediator(session).send(CompleteTaskInstanceCommand(
                user_id=actor['id'], task_instance_id=workflow['task_instance']['id'])).next_task_instance.id
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix='generation') as gpool, \
         ThreadPoolExecutor(max_workers=1, thread_name_prefix='completion') as cpool:
        generating = gpool.submit(generate)
        finishing = cpool.submit(finish)
        assert generating.result(timeout=20) == 2
        assert finishing.result(timeout=20) is not None
