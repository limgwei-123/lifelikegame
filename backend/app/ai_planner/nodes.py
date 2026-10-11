from typing import Any

from app.ai_planner.providers.base import AIPlannerProvider, PlannerRequest
from app.ai_planner.schemas import AiPlannerResponse, ConversationMessage
from app.ai_planner.state import AiPlannerGraphState

def generate_ai_response_node(
    state: AiPlannerGraphState, *, provider: AIPlannerProvider,
) -> dict[str, Any]:
    payload = state["payload"]

    result = provider.generate_plan(PlannerRequest(
        user_prompt=payload.user_prompt,
        conversation_history=payload.conversation_history,
    ))
    data = result.model_dump()

    return {
        "data": data,
        "status": data.get("status"),
        "message": data.get("message", ""),
        "questions": data.get("questions", []),
        "plan": data.get("plan"),
    }


def build_response_node(state: AiPlannerGraphState) -> dict[str, Any]:
    payload = state["payload"]
    data = state["data"]

    ai_response = AiPlannerResponse.model_validate(data)

    updated_history = build_updated_history(
        old_history=payload.conversation_history,
        user_prompt=payload.user_prompt,
        ai_response=ai_response,
    )

    ai_response.conversation_history = updated_history

    return {
        "ai_response": ai_response,
    }


def build_updated_history(
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
        assistant_content += (
            f"\nPlan Preview:\n"
            f"Target：{ai_response.plan.goal_title}\n"
            f"Task:\n{task_titles}"
        )

    return [
        *old_history,
        ConversationMessage(role="user", content=user_prompt),
        ConversationMessage(role="assistant", content=assistant_content),
    ]
