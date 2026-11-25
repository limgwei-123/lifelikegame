from datetime import datetime, timedelta, timezone
from app.shared import dates

from app.errors.exception import NotFoundError
from app.progress.models import TaskCompletion
from app.progress.repository import ProgressRepository
from app.progress.schemas import BossRosterEntry, BossState, ProgressResponse
from app.users.repository import UserRepository


BOSSES = (
    ('slime', '软糖史莱姆', 2), ('cloud', '困困云怪', 4),
    ('mushroom', '蘑菇守卫', 7), ('pillow', '抱枕巨兽', 12),
    ('stone', '小石头人', 20), ('dragon', '皇冠小龙', 30),
)


def utc_now():
    return dates.utc_now()


def boss_progress(total_damage):
    remaining, round_index, position = total_damage, 0, 0
    while remaining >= BOSSES[position][2] + round_index * 30:
        remaining -= BOSSES[position][2] + round_index * 30
        position += 1
        if position == len(BOSSES):
            round_index += 1
            position = 0
    boss_id, name, base_hp = BOSSES[position]
    max_hp = base_hp + round_index * 30
    return (
        BossState(id=boss_id, name=name, round=round_index + 1, position=position + 1,
                  hp=max_hp - remaining, max_hp=max_hp),
        round_index * len(BOSSES) + position,
        [BossRosterEntry(id=key, name=label, max_hp=hp + round_index * 30,
                         status='defeated' if i < position else 'current' if i == position else 'upcoming')
         for i, (key, label, hp) in enumerate(BOSSES)],
    )


def streaks(days, today):
    active = set(days)
    previous, run, longest = None, 0, 0
    for day in sorted(active):
        run = run + 1 if previous is not None and day == previous + timedelta(days=1) else 1
        longest = max(longest, run)
        previous = day
    cursor = today if today in active else today - timedelta(days=1)
    current = 0
    while cursor in active:
        current += 1
        cursor -= timedelta(days=1)
    return current, longest


class ProgressService:
    def __init__(self, repository: ProgressRepository, users: UserRepository, clock=None):
        self.repository = repository
        self.users = users
        self.clock = clock or utc_now

    def current_time(self, at: datetime | None = None) -> datetime:
        now = at if at is not None else self.clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError('Progress clock must be timezone-aware')
        return now.astimezone(timezone.utc)

    @staticmethod
    def _zone(user):
        zone = dates.player_zone(user.timezone)
        return zone.key, zone

    def record_completion(self, user_id, task_instance_id, is_goal_task, *, completed_at: datetime | None = None):
        # Instance locking is owned by TaskInstanceService. This second lock
        # serializes distinct-instance completions for one user, not all players.
        user = self.users.get_by_id_for_update(user_id)
        if user is None:
            raise NotFoundError('User not found')
        if self.repository.get_completion(user_id, task_instance_id) is not None:
            return
        zone_name, zone = self._zone(user)
        now = self.current_time(completed_at)
        self.repository.add(TaskCompletion(
            user_id=user_id, task_instance_id=task_instance_id,
            completed_at=now, completed_local_date=now.astimezone(zone).date(),
            timezone=zone_name, is_goal_task=is_goal_task,
        ))

    def get_progress(self, user_id, *, as_of: datetime | None = None):
        user = self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError('User not found')
        zone_name, zone = self._zone(user)
        today = self.current_time(as_of).astimezone(zone).date()
        days = self.repository.daily_counts(user_id)
        total = sum(row.completed_count for row in days)
        damage = sum(row.damage for row in days)
        completed_today = sum(row.completed_count for row in days if row.completed_local_date == today)
        current, longest = streaks([row.completed_local_date for row in days], today)
        boss, defeated, roster = boss_progress(damage)
        return ProgressResponse(
            timezone=zone_name, today=today, total_completed=total, completed_today=completed_today,
            total_damage=damage, current_streak=current, longest_streak=longest,
            defeated_bosses=defeated, boss=boss, bosses=roster,
        )
