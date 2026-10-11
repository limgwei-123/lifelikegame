from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field


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
    tasks: list[GeneratedTask]


class PlannerRequest(BaseModel):
    user_prompt: str
    conversation_history: list[ConversationMessage] = Field(default_factory=list)


class PlannerResult(BaseModel):
    status: Literal["need_more_info", "plan_ready"]
    message: str
    questions: list[str] = Field(default_factory=list)
    plan: GeneratedPlan | None = None


class AIPlannerProvider(Protocol):
    def generate_plan(self, request: PlannerRequest) -> PlannerResult: ...
