from pydantic import BaseModel
from typing import Any

class GeneratedPlanTask(BaseModel):
    title: str
    description: str | None = None
    schedule_type: str
    schedule_value_json: dict[str, Any]

class GeneratedPlan(BaseModel):
    plan_type: str
    user_prompt: str

class AiPlannerResponse(BaseModel):
    message: str
    plan: GeneratedPlan