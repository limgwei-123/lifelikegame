from google import genai
from google.genai import types

from app.ai_planner.extract_json import extract_json
from app.ai_planner.prompts import build_generate_plan_prompt
from app.ai_planner.providers.base import PlannerRequest, PlannerResult


class GeminiPlannerProvider:
    def __init__(self, *, api_key: str | None, model: str | None):
        self.api_key = api_key
        self.model = model

    def generate_plan(self, request: PlannerRequest) -> PlannerResult:
        if not self.api_key or not self.model:
            raise RuntimeError("AI_API_KEY and AI_MODEL must be set to use AI Planner")

        prompt = build_generate_plan_prompt(
            user_prompt=request.user_prompt,
            conversation_history=request.conversation_history,
        )
        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(
            model=self.model, contents=prompt, config=types.GenerateContentConfig(),
        )
        data = extract_json(response.text)
        # Preserve the existing Gemini schedule repair before typed validation.
        plan = data.get("plan")
        if data.get("status") == "plan_ready" and plan:
            for task in plan.get("tasks", []):
                schedule_value = task.get("schedule_value_json") or {}
                if task.get("schedule_type") == "daily":
                    task["schedule_value_json"] = {}
                elif task.get("schedule_type") == "weekly":
                    days = schedule_value.get("days") if isinstance(schedule_value, dict) else None
                    if not days:
                        task["schedule_value_json"] = {"days": [1, 3, 5]}
        return PlannerResult.model_validate(data)
