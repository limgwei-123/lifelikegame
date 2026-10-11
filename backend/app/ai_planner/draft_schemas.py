from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.ai_planner.providers.base import MAX_GENERATED_TASKS


Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Weekday = Annotated[int, Field(strict=True, ge=0, le=6)]


class WeeklyDraftValue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    days: list[Weekday] = Field(min_length=1)


class DraftTask(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Title
    description: str | None = None
    scoring_scheme_id: Annotated[int, Field(strict=True, gt=0)] | None = None
    schedule_type: Literal["daily", "weekly"]
    schedule_value_json: dict

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.schedule_type == "daily":
            if self.schedule_value_json:
                raise ValueError("Daily schedule value must be empty")
        else:
            value = WeeklyDraftValue.model_validate(self.schedule_value_json)
            self.schedule_value_json = {"days": sorted(set(value.days))}
        return self


class DraftPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    goal_title: Title
    tasks: list[DraftTask] = Field(min_length=1, max_length=MAX_GENERATED_TASKS)


class DraftResponse(BaseModel):
    draft_id: UUID
    plan: DraftPlan
