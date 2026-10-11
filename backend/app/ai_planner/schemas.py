from pydantic import BaseModel
from typing import Literal
from uuid import UUID
from app.ai_planner.providers.base import ConversationMessage, GeneratedPlan, GeneratedTask

class AiPlannerResponse(BaseModel):
    status: Literal["need_more_info", "plan_ready"]
    message: str
    questions: list[str] = []
    plan: GeneratedPlan | None = None
    draft_id: UUID | None = None
    conversation_history: list[ConversationMessage] = []

class AiPlannerChatRequest(BaseModel):
    user_prompt: str
    conversation_history: list[ConversationMessage] = []
