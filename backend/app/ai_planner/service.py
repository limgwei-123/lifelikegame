import json
from app.ai_planner.schemas import GeneratedPlan, AiPlannerResponse
from app.ai_planner.prompts import build_generate_plan_prompt
from app.ai_planner.extract_json import extract_json

from google import genai
from google.genai import types

import os


api_key = os.getenv("AI_API_KEY")
model = os.getenv("AI_MODEL")

class AIPlannerService:
    def generate_plan(self, payload: GeneratedPlan) -> AiPlannerResponse:
        prompt = build_generate_plan_prompt(
            user_prompt=payload.user_prompt,
            plan_type=payload.plan_type
        )

        raw_result = self._call_ai(prompt)
        print("======== RAW RESULT ========")
        print(raw_result)
        print("============================")

        data = extract_json(raw_result)

        return AiPlannerResponse(**data)

    def _call_ai(self, prompt: str) -> str:
        client = genai.Client(api_key=api_key)
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )

        return response.text
        raise NotImplementedError