import json
from app.ai_planner.schemas import AiPlannerChatRequest, AiPlannerResponse,ConversationMessage

from app.ai_planner.prompts import build_generate_plan_prompt
from app.ai_planner.extract_json import extract_json

from google import genai
from google.genai import types

import os


api_key = os.getenv("AI_API_KEY")
model = os.getenv("AI_MODEL")

class AIPlannerService:

    def generate_plan(self, payload: AiPlannerChatRequest) -> AiPlannerResponse:
        prompt = build_generate_plan_prompt(
            user_prompt=payload.user_prompt,
            conversation_history=payload.conversation_history
        )

        raw_result = self._call_ai(prompt)

        data = extract_json(raw_result)
        data = self._normalize_plan_schedule(data)

        ai_response = AiPlannerResponse.model_validate(data)

        updated_history = self._build_updated_history(
            old_history=payload.conversation_history,
            user_prompt=payload.user_prompt,
            ai_response=ai_response,
        )

        ai_response.conversation_history = updated_history

        return (ai_response)

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

    def _build_updated_history(
        self,
        old_history: list[ConversationMessage],
        user_prompt: str,
        ai_response: AiPlannerResponse,
    ) -> list[ConversationMessage]:

        assistant_content = ai_response.message

        if ai_response.questions:
            questions_text = "\n".join(
                f"{index + 1}. {question}"
                for index, question in enumerate(ai_response.questions)
            )
            assistant_content += f"\nQuestion: \n{questions_text}"

        if ai_response.plan:
            task_titles = "\n".join(
                f"{index + 1}. {task.title}"
                for index, task in enumerate(ai_response.plan.tasks)
            )
            assistant_content += f"\nPlan Preview:\nTarget：{ai_response.plan.goal_title}\nTask:\n{task_titles}"


        return [
            *old_history,
            ConversationMessage(role="user", content=user_prompt),
            ConversationMessage(role="assistant", content=assistant_content),
        ]

    def _normalize_plan_schedule(self, data: dict) -> dict:
        plan = data.get("plan")
        if not plan:
            return data

        for task in plan.get("tasks", []):
            schedule_type = task.get("schedule_type")
            schedule_value = task.get("schedule_value_json") or {}

            if schedule_type == "daily":
                task["schedule_value_json"] = {}

            if schedule_type == "weekly":
                days = schedule_value.get("days")
                if not days:
                    task["schedule_value_json"] = {"days": [1, 3, 5]}

        return data