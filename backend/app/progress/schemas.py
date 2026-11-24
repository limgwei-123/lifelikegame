from datetime import date
from typing import Literal

from pydantic import BaseModel


class BossState(BaseModel):
    id: str
    name: str
    round: int
    position: int
    hp: int
    max_hp: int


class BossRosterEntry(BaseModel):
    id: str
    name: str
    max_hp: int
    status: Literal['defeated', 'current', 'upcoming']


class ProgressResponse(BaseModel):
    timezone: str
    today: date
    total_completed: int
    completed_today: int
    total_damage: int
    current_streak: int
    longest_streak: int
    defeated_bosses: int
    boss: BossState
    bosses: list[BossRosterEntry]
