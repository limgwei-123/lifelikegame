import json
from typing import NoReturn

from google import genai
from google.genai import types

from app.ai_planner.prompts import build_generate_plan_prompt
from app.ai_planner.providers.base import PlannerRequest, PlannerResult


def _reject_non_json_number(value: str) -> NoReturn:
    raise ValueError(f"AI Planner output contains an invalid JSON number: {value}")


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
            model=self.model, contents=prompt, config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=PlannerResult.model_json_schema(),
            ),
        )
        raw = response.text
        if not raw or not raw.strip():
            raise ValueError("AI Planner returned an empty response")
        data = json.loads(raw, parse_constant=_reject_non_json_number)
        result = PlannerResult.model_validate(data, strict=True)
        # Keep existing defaults, but only after the output passes validation.
        if result.plan is not None:
            for task in result.plan.tasks:
                if task.schedule_type == "daily":
                    task.schedule_value_json = {}
                elif not task.schedule_value_json.get("days"):
                    task.schedule_value_json = {"days": [1, 3, 5]}
        return result
