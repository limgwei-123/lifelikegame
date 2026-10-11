import pytest

from app.ai_planner.prompts import build_generate_plan_prompt
from app.ai_planner.providers.base import ConversationMessage
from app.ai_planner.schemas import AiPlannerChatRequest
from app.ai_planner.service import AIPlannerService


def history_section(prompt):
    return prompt.split("Conversation history:\n", 1)[1].rstrip("\n")


def test_prompt_keeps_only_six_recent_messages_in_order_without_mutating_history():
    history = [ConversationMessage(role="user" if i % 2 == 0 else "assistant", content=f"Message {i}")
               for i in range(10)]
    before = [message.model_dump() for message in history]
    prompt = build_generate_plan_prompt("Current request", history)
    assert history_section(prompt).splitlines() == [
        "user: Message 4", "assistant: Message 5", "user: Message 6",
        "assistant: Message 7", "user: Message 8", "assistant: Message 9",
    ]
    assert [message.model_dump() for message in history] == before


def test_prompt_bounds_long_messages_and_total_history_preferring_recent_context():
    history = [ConversationMessage(role="user", content=f"Message {i}: " + "x" * 2000) for i in range(10)]
    section = history_section(build_generate_plan_prompt("Current request", history))
    assert len(section) <= 4000
    assert "Message 9:" in section
    assert "Message 0:" not in section
    assert "[truncated]" in section
    assert all(len(line.removeprefix("user: ")) <= 1000 for line in section.splitlines())
    assert section.index("Message 8:") < section.index("Message 9:")
    assert len(history[-1].content) > 2000


def test_current_request_is_not_truncated_by_history_budget():
    current = "Current goal: " + "z" * 7000 + " Friday only"
    history = [ConversationMessage(role="assistant", content="x" * 10000)] * 20
    prompt = build_generate_plan_prompt(current, history)
    assert f"User request:\n{current}\n" in prompt
    assert len(history_section(prompt)) <= 4000


def test_short_history_keeps_weekday_constraints_and_roles():
    history = [ConversationMessage(role="user", content="Friday only"),
               ConversationMessage(role="assistant", content="How long each day?")]
    assert history_section(build_generate_plan_prompt("20 minutes", history)) == (
        "user: Friday only\nassistant: How long each day?"
    )


def test_trimming_ai_context_does_not_trim_returned_chat_history():
    from app.ai_planner.providers.base import PlannerResult

    class Provider:
        def generate_plan(self, request):
            section = history_section(build_generate_plan_prompt(request.user_prompt, request.conversation_history))
            assert "Earlier 0" not in section
            assert "Earlier 9" in section
            return PlannerResult(status="need_more_info", message="When?")

    payload = AiPlannerChatRequest(user_prompt="Fitness", conversation_history=[
        ConversationMessage(role="user", content=f"Earlier {i}") for i in range(10)
    ])
    response = AIPlannerService(Provider()).generate_plan(payload)
    assert len(response.conversation_history) == 12
    assert response.conversation_history[:10] == payload.conversation_history
    assert response.conversation_history[-2].content == "Fitness"
    assert response.conversation_history[-1].content == "When?"
    assert len(payload.conversation_history) == 10


def test_manual_task_creation_is_not_limited_to_three(client, auth_headers, goal, scoring_scheme):
    for i in range(4):
        response = client.post(f"/goals/{goal['id']}/tasks", headers=auth_headers, json={
            "title": f"Manual task {i}", "scoring_scheme_id": scoring_scheme["id"],
        })
        assert response.status_code in (200, 201), response.text


@pytest.mark.parametrize("count", [0, 4])
def test_confirm_rejects_invalid_ai_task_count_before_writing_data(client, auth_headers, db, count):
    from app.goals.models import Goal
    from app.tasks.models import Task

    goals_before = db.query(Goal).count()
    tasks_before = db.query(Task).count()
    response = client.post("/workflows/ai/confirm", headers=auth_headers, json={"plan": {
        "goal_title": "Fitness", "tasks": [
            {"title": f"Walk {i}", "schedule_type": "daily", "schedule_value_json": {}}
            for i in range(count)
        ],
    }})
    assert response.status_code == 422, response.text
    assert response.json()["detail"][0]["loc"] == ["body", "plan", "tasks"]
    assert db.query(Goal).count() == goals_before
    assert db.query(Task).count() == tasks_before
