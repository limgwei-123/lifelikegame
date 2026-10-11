from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_GENERATED_TASKS = 3


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class GeneratedTask(BaseModel):
    title: str
    description: str | None = None
    schedule_type: Literal["daily", "weekly"]
    schedule_value_json: dict[str, Any]


class GeneratedPlan(BaseModel):
    goal_title: str
    tasks: list[GeneratedTask] = Field(min_length=1, max_length=MAX_GENERATED_TASKS)


class PlannerRequest(BaseModel):
    user_prompt: str
    conversation_history: list[ConversationMessage] = Field(default_factory=list)


class PlannerResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["need_more_info", "plan_ready"]
    message: str
    questions: list[str] = Field(default_factory=list)
    plan: GeneratedPlan | None = None

    @model_validator(mode="after")
    def validate_status(self) -> "PlannerResult":
        if self.status == "plan_ready":
            if self.plan is None or not self.plan.tasks:
                raise ValueError("plan_ready requires a plan with tasks")
            if self.questions:
                raise ValueError("plan_ready must not include questions")
        elif self.plan is not None:
            raise ValueError("need_more_info must not include a plan")
        return self


class AIPlannerProvider(Protocol):
    def generate_plan(self, request: PlannerRequest) -> PlannerResult: ...
