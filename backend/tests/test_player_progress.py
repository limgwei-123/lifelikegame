from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from threading import Barrier

import pytest
from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from app.task_instances.commands import CompleteTaskInstanceCommand
from app.task_instances.dependencies import build_complete_task_instance_mediator
from app.task_instances.models import TaskInstance
from app.task_schedules.models import TaskSchedule
from app.tasks.models import Task
from app.users.models import User
from app.point_ledgers.models import PointLedger


def progress(client, actor):
    response = client.get('/progress', headers=actor['headers'])
    assert response.status_code == 200, response.text
    return response.json()


def clock(monkeypatch, value):
    from app.progress import service
    monkeypatch.setattr(service, 'utc_now', lambda: datetime.fromisoformat(value))


def instance(db, actor, goal=True, status='todo', levels=None):
    user_id = actor['user'].id
    task = Task(user_id=user_id, goal_id=actor['rows']['goals'].id if goal else None,
                title='Progress task', scoring_scheme_json={'normal': 5, 'great': 12} if goal else None)
    db.add(task)
    db.flush()
    schedule = TaskSchedule(user_id=user_id, task_id=task.id, schedule_type='once',
                            schedule_value_json={}, start_date=date(2045, 5, 10))
    db.add(schedule)
    db.flush()
    row = TaskInstance(user_id=user_id, task_id=task.id, task_schedule_id=schedule.id,
                       date_instance=date(2045, 5, 10), status=status,
                       score_awarded=5 if status == 'done' and goal else 0,
                       scoring_snapshot_json=(levels if levels is not None else {'normal': 5, 'great': 12}) if goal else None)
    db.add(row)
    db.commit()
    result = {'id': row.id, 'task_id': task.id, 'schedule_id': schedule.id}
    db.rollback()
    return result


def complete(client, actor, row, goal=True, level='normal'):
    response = client.post(f"/task_instances/{row['id']}/complete", headers=actor['headers'],
                           json={'completion_level': level} if goal else {})
    assert response.status_code == 200, response.text
    assert response.json().get('progress') is not None
    return response.json()


def record_count(db, user_id):
    from app.progress.models import TaskCompletion
    with Session(db.get_bind()) as reader:
        return reader.query(TaskCompletion).filter_by(user_id=user_id).count()


def test_players_start_from_zero_and_cannot_select_another_players_progress(client, ownership_case):
    owner, other = ownership_case['owner'], ownership_case['other']
    for actor in (owner, other):
        data = progress(client, actor)
        assert data['total_completed'] == data['total_damage'] == data['current_streak'] == 0
        assert data['boss']['id'] == 'slime'
        assert data['boss']['hp'] == data['boss']['max_hp'] == 2
        assert data['boss']['round'] == data['boss']['position'] == 1
        assert data['defeated_bosses'] == 0
    assert client.get('/progress').status_code == 401
    response = client.get('/progress', headers=owner['headers'], params={'user_id': str(other['user'].id)})
    assert response.json() == progress(client, owner)
    assert client.post('/progress', headers=owner['headers'], json={'total_damage': 1000}).status_code == 405


def test_first_goal_completion_updates_only_its_player_and_returns_summary(client, ownership_case):
    owner, other = ownership_case['owner'], ownership_case['other']
    progress(client, owner)
    row = {'id': owner['rows']['task_instances'].id}
    data = complete(client, owner, row)['progress']
    assert data['total_completed'] == data['total_damage'] == data['completed_today'] == data['current_streak'] == 1
    assert data['boss']['hp'] == 1
    assert progress(client, owner) == data
    assert progress(client, other)['total_damage'] == 0


def test_todo_counts_for_streak_but_not_boss_or_points(client, db, ownership_case):
    owner = ownership_case['owner']
    progress(client, owner)
    row = instance(db, owner, goal=False)
    result = complete(client, owner, row, goal=False)
    data = result['progress']
    assert data['total_completed'] == data['current_streak'] == 1
    assert data['total_damage'] == 0 and data['boss']['hp'] == 2
    assert result['point_ledger'] is None and result['user']['current_value'] == 100


def test_retries_and_rescoring_preserve_the_first_completion_fact(client, db, ownership_case):
    owner = ownership_case['owner']
    progress(client, owner)
    row = instance(db, owner)
    first = complete(client, owner, row)
    for level in ('normal', 'great', 'great', 'normal'):
        result = complete(client, owner, row, level=level)
        assert result['progress'] == first['progress']
    assert record_count(db, owner['user'].id) == 1


@pytest.mark.parametrize('goal', [True, False])
def test_legacy_done_records_are_not_backfilled_on_retry(client, db, ownership_case, goal):
    owner = ownership_case['owner']
    progress(client, owner)
    row = instance(db, owner, goal=goal, status='done')
    result = complete(client, owner, row, goal=goal)
    assert result['progress']['total_completed'] == result['progress']['total_damage'] == 0
    assert record_count(db, owner['user'].id) == 0


def test_zero_point_goal_still_deals_one_damage(client, db, ownership_case):
    owner = ownership_case['owner']
    progress(client, owner)
    row = instance(db, owner, levels={'normal': 0})
    result = complete(client, owner, row)
    assert result['task_instance']['score_awarded'] == 0 and result['point_ledger'] is None
    assert result['progress']['total_damage'] == 1


def test_completion_records_actual_local_day_not_scheduled_date(client, db, ownership_case, monkeypatch):
    owner = ownership_case['owner']
    progress(client, owner)
    clock(monkeypatch, '2026-11-24T15:59:00+00:00')
    first = instance(db, owner)
    data = complete(client, owner, first)['progress']
    assert data['today'] == '2026-11-24' and data['current_streak'] == 1
    clock(monkeypatch, '2026-11-24T16:01:00+00:00')
    second = instance(db, owner, goal=False)
    data = complete(client, owner, second, goal=False)['progress']
    assert data['today'] == '2026-11-25'
    assert data['current_streak'] == data['longest_streak'] == 2
    assert data['completed_today'] == 1 and data['total_damage'] == 1
    from app.progress.models import TaskCompletion
    with Session(db.get_bind()) as reader:
        facts = reader.query(TaskCompletion).filter_by(user_id=owner['user'].id).order_by(TaskCompletion.completed_at).all()
        assert [fact.completed_local_date for fact in facts] == [date(2026, 11, 24), date(2026, 11, 25)]
        assert all(fact.timezone == 'Asia/Kuala_Lumpur' for fact in facts)
        assert facts[0].completed_at == datetime(2026, 11, 24, 15, 59, tzinfo=timezone.utc)


def test_multiple_completions_same_day_and_streak_gap(client, db, ownership_case, monkeypatch):
    owner = ownership_case['owner']
    progress(client, owner)
    for day in (20, 21, 22, 22):
        clock(monkeypatch, f'2026-11-{day}T05:00:00+00:00')
        complete(client, owner, instance(db, owner))
    data = progress(client, owner)
    assert data['current_streak'] == data['longest_streak'] == 3
    assert data['completed_today'] == 2 and data['total_completed'] == 4
    clock(monkeypatch, '2026-11-23T05:00:00+00:00')
    assert progress(client, owner)['current_streak'] == 3  # Still has today to continue.
    clock(monkeypatch, '2026-11-24T05:00:00+00:00')
    assert progress(client, owner)['current_streak'] == 0
    complete(client, owner, instance(db, owner))
    data = progress(client, owner)
    assert data['current_streak'] == 1 and data['longest_streak'] == 3


def test_completion_history_survives_soft_and_hard_task_deletion(client, db, ownership_case):
    owner = ownership_case['owner']
    progress(client, owner)
    row = instance(db, owner)
    expected = complete(client, owner, row)['progress']
    assert client.post(f"/tasks/{row['task_id']}/delete", headers=owner['headers']).status_code == 204
    assert progress(client, owner) == expected
    with Session(db.get_bind()) as writer:
        writer.execute(delete(Task).where(Task.id == row['task_id']))
        writer.commit()
    assert progress(client, owner) == expected
    assert client.post(f"/goals/{owner['rows']['goals'].id}/delete", headers=owner['headers']).status_code == 204
    assert progress(client, owner) == expected


def test_recording_failure_rolls_back_status_points_and_history(client, db, ownership_case, monkeypatch):
    owner = ownership_case['owner']
    progress(client, owner)
    row = instance(db, owner)
    from app.progress.repository import ProgressRepository
    original = ProgressRepository.add

    def fail_after_flush(self, record):
        original(self, record)
        raise RuntimeError('completion history failure')

    monkeypatch.setattr(ProgressRepository, 'add', fail_after_flush)
    with pytest.raises(RuntimeError, match='completion history failure'):
        client.post(f"/task_instances/{row['id']}/complete", headers=owner['headers'], json={'completion_level': 'normal'})
    with Session(db.get_bind()) as reader:
        assert reader.get(TaskInstance, row['id']).status == 'todo'
        assert reader.get(User, owner['user'].id).current_value == 100
        assert reader.query(PointLedger).filter_by(user_id=owner['user'].id).count() == 1
    assert record_count(db, owner['user'].id) == 0


def test_commit_failure_rolls_back_completion_and_progress(client, db, ownership_case, monkeypatch):
    owner = ownership_case['owner']
    progress(client, owner)
    row = instance(db, owner)
    from app.core.unit_of_work import UnitOfWork
    def fail(self):
        raise RuntimeError('commit failed')
    monkeypatch.setattr(UnitOfWork, 'commit', fail)
    with pytest.raises(RuntimeError, match='commit failed'):
        client.post(f"/task_instances/{row['id']}/complete", headers=owner['headers'], json={'completion_level': 'normal'})
    with Session(db.get_bind()) as reader:
        assert reader.get(TaskInstance, row['id']).status == 'todo'
        assert reader.get(User, owner['user'].id).current_value == 100
    assert record_count(db, owner['user'].id) == 0


@pytest.mark.parametrize('same_instance', [True, False])
def test_concurrent_goal_completions_do_not_lose_or_duplicate_damage(client, db, ownership_case, same_instance):
    owner = ownership_case['owner']
    progress(client, owner)
    rows = [instance(db, owner)]
    rows.append(rows[0] if same_instance else instance(db, owner))
    user_id, bind, ready = owner['user'].id, db.get_bind(), Barrier(2)
    def worker(row):
        with Session(bind) as session:
            session.execute(text("SET LOCAL lock_timeout = '10s'"))
            ready.wait(timeout=10)
            result = build_complete_task_instance_mediator(session).send(CompleteTaskInstanceCommand(
                task_instance_id=row['id'], user_id=user_id, completion_level='normal',
            ))
            return result.progress.total_damage
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, row) for row in rows]
        results = [future.result(timeout=20) for future in futures]
    expected = 1 if same_instance else 2
    assert progress(client, owner)['total_damage'] == expected
    assert record_count(db, user_id) == expected
    assert sorted(results) == ([1, 1] if same_instance else [1, 2])


def test_foreign_deleted_and_invalid_requests_do_not_create_progress(client, db, ownership_case):
    owner, other = ownership_case['owner'], ownership_case['other']
    progress(client, owner)
    row = instance(db, owner)
    assert client.post(f"/task_instances/{row['id']}/complete", headers=other['headers'], json={'completion_level': 'normal'}).status_code == 404
    assert client.post(f"/task_instances/{row['id']}/complete", headers=owner['headers'], json={'completion_level': 'invalid'}).status_code == 422
    assert record_count(db, owner['user'].id) == record_count(db, other['user'].id) == 0
    owner['user'].deleted_at = datetime.now(timezone.utc)
    db.commit()
    assert client.get('/progress', headers=owner['headers']).status_code == 401


def test_invalid_user_timezone_aborts_completion_without_awarding(client, db, ownership_case):
    owner = ownership_case['owner']
    progress(client, owner)
    row = instance(db, owner)
    user_id = owner['user'].id
    owner['user'].timezone = 'Invalid/Timezone'
    db.commit()
    response = client.post(f"/task_instances/{row['id']}/complete", headers=owner['headers'], json={'completion_level': 'normal'})
    assert response.status_code == 422
    with Session(db.get_bind()) as reader:
        assert reader.get(TaskInstance, row['id']).status == 'todo'
        assert reader.get(User, user_id).current_value == 100
    assert record_count(db, user_id) == 0


@pytest.mark.parametrize('damage,boss_id,hp,round_number,defeated', [
    (0, 'slime', 2, 1, 0), (1, 'slime', 1, 1, 0), (2, 'cloud', 4, 1, 1),
    (6, 'mushroom', 7, 1, 2), (13, 'pillow', 12, 1, 3), (25, 'stone', 20, 1, 4),
    (45, 'dragon', 30, 1, 5), (74, 'dragon', 1, 1, 5), (75, 'slime', 32, 2, 6),
    (76, 'slime', 31, 2, 6), (106, 'slime', 1, 2, 6), (107, 'cloud', 34, 2, 7),
    (140, 'cloud', 1, 2, 7), (141, 'mushroom', 37, 2, 8),
    (330, 'slime', 62, 3, 12), (392, 'cloud', 64, 3, 13),
])
def test_boss_loop_boundaries(damage, boss_id, hp, round_number, defeated):
    from app.progress.service import boss_progress
    boss, beaten, roster = boss_progress(damage)
    assert (boss.id, boss.hp, boss.round, beaten) == (boss_id, hp, round_number, defeated)
    assert len(roster) == 6 and sum(row.status == 'current' for row in roster) == 1
    assert roster[boss.position - 1].max_hp == boss.max_hp


def test_progress_projection_reads_stored_damage_and_round_from_records(client, db, ownership_case):
    owner, other = ownership_case['owner'], ownership_case['other']
    progress(client, owner)
    from app.progress.models import TaskCompletion
    for i in range(76):
        db.add(TaskCompletion(user_id=owner['user'].id, task_instance_id=1000000 + i,
                              completed_at=datetime.now(timezone.utc), completed_local_date=date.today(),
                              timezone='Asia/Kuala_Lumpur', is_goal_task=i < 75))
    db.commit()
    data = progress(client, owner)
    assert data['total_completed'] == 76 and data['total_damage'] == 75
    assert data['boss']['id'] == 'slime' and data['boss']['hp'] == data['boss']['max_hp'] == 32
    assert data['defeated_bosses'] == 6 and data['boss']['round'] == 2
    assert progress(client, other)['total_completed'] == 0


def test_each_players_timezone_is_used_at_the_same_utc_instant(client, db, ownership_case, monkeypatch):
    owner, other = ownership_case['owner'], ownership_case['other']
    progress(client, owner)
    other['user'].timezone = 'UTC'
    db.commit()
    clock(monkeypatch, '2026-11-24T16:30:00+00:00')
    owner_result = complete(client, owner, instance(db, owner))['progress']
    other_result = complete(client, other, instance(db, other))['progress']
    assert owner_result['today'] == '2026-11-25'
    assert other_result['today'] == '2026-11-24'
    assert owner_result['total_damage'] == other_result['total_damage'] == 1


def test_dst_repeated_hour_counts_as_one_local_day(client, db, ownership_case, monkeypatch):
    owner = ownership_case['owner']
    progress(client, owner)
    owner['user'].timezone = 'America/New_York'
    db.commit()
    for timestamp in ('2026-11-01T05:30:00+00:00', '2026-11-01T06:30:00+00:00'):
        clock(monkeypatch, timestamp)
        complete(client, owner, instance(db, owner))
    data = progress(client, owner)
    assert data['current_streak'] == 1 and data['completed_today'] == 2
    clock(monkeypatch, '2026-11-02T05:01:00+00:00')
    data = complete(client, owner, instance(db, owner))['progress']
    assert data['today'] == '2026-11-02' and data['current_streak'] == 2


def test_rescoring_on_another_day_does_not_extend_streak(client, db, ownership_case, monkeypatch):
    owner = ownership_case['owner']
    progress(client, owner)
    row = instance(db, owner)
    clock(monkeypatch, '2026-11-20T05:00:00+00:00')
    complete(client, owner, row)
    clock(monkeypatch, '2026-11-22T05:00:00+00:00')
    data = complete(client, owner, row, level='great')['progress']
    assert data['current_streak'] == data['completed_today'] == 0
    assert data['total_completed'] == data['total_damage'] == 1


def test_another_player_can_complete_while_one_player_row_is_locked(client, db, ownership_case):
    owner, other = ownership_case['owner'], ownership_case['other']
    progress(client, owner)
    row = instance(db, other)
    owner_id, other_id, bind = owner['user'].id, other['user'].id, db.get_bind()
    def worker():
        with Session(bind) as session:
            session.execute(text("SET LOCAL lock_timeout = '3s'"))
            return build_complete_task_instance_mediator(session).send(CompleteTaskInstanceCommand(
                task_instance_id=row['id'], user_id=other_id, completion_level='normal',
            )).progress.total_damage
    with Session(bind) as locker:
        locker.get(User, owner_id, with_for_update=True)
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                assert pool.submit(worker).result(timeout=8) == 1
        finally:
            locker.rollback()
    assert progress(client, owner)['total_damage'] == 0
