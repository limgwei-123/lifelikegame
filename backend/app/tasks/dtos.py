from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class CreateTaskDTO:
  title: str
  description: str | None = None
  is_active: bool = True
  scoring_scheme_id: int | None = None
  scoring_scheme_json: dict | None = None
  is_scoring_scheme_locked: bool = False


@dataclass(frozen=True, slots=True)
class UpdateTaskDTO:
  changes: dict[str, Any] = field(default_factory=dict)
