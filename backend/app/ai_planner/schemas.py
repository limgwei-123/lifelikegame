from pydantic import BaseModel
from typing import Any, Literal

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

class AiPlannerResponse(BaseModel):
    status: Literal["need_more_info", "plan_ready"]
    message: str
    questions: list[str] = []
    plan: GeneratedPlan | None = None
    conversation_history: list[ConversationMessage] = []

class AiPlannerChatRequest(BaseModel):
    user_prompt: str
    conversation_history: list[ConversationMessage] = []