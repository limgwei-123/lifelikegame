import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from google.genai import types

from app.ai_planner.providers import gemini
from app.ai_planner.errors import AIInvalidOutputError
from app.ai_planner.providers.base import PlannerResult
from app.ai_planner.schemas import AiPlannerChatRequest
from app.ai_planner.service import AIPlannerService


VALID_PLAN = {
    "goal_title": "Fitness", "tasks": [{
        "title": "Walk", "schedule_type": "daily", "schedule_value_json": {},
    }],
}
READY = {"status": "plan_ready", "message": "Ready", "questions": [], "plan": VALID_PLAN}
FOLLOW_UP = {"status": "need_more_info", "message": "When?", "questions": ["Which days?"], "plan": None}


@pytest.fixture
def generate_content(monkeypatch):
    generate = Mock()
    monkeypatch.setattr(gemini.genai, "Client", lambda **kwargs: SimpleNamespace(
        models=SimpleNamespace(generate_content=generate), close=Mock(),
    ))
    return generate


def run_planner(generate_content, raw):
    generate_content.return_value = types.GenerateContentResponse(candidates=[types.Candidate(
        content=types.Content(parts=[types.Part(text=raw)]),
    )]) if raw is not None else types.GenerateContentResponse()
    service = AIPlannerService(gemini.GeminiPlannerProvider(api_key="test-key", model="test-model"))
    return service.generate_plan(AiPlannerChatRequest(user_prompt="Fitness"))


def test_gemini_requests_json_output_with_explicit_plan_schema(generate_content):
    run_planner(generate_content, json.dumps(READY))
    config = generate_content.call_args.kwargs["config"]
    assert config.response_mime_type == "application/json"
    schema = config.response_json_schema
    assert schema["type"] == "object"
    assert schema["properties"]["status"]["enum"] == ["need_more_info", "plan_ready"]
    assert {"status", "message"} <= set(schema["required"])
    assert schema["$defs"]["GeneratedPlan"]["required"] == ["goal_title", "tasks"]
    assert schema["$defs"]["GeneratedTask"]["properties"]["schedule_type"]["enum"] == ["daily", "weekly"]


def test_real_sdk_serializes_schema_into_http_request_without_network(monkeypatch):
    import httpx

    def handle(request):
        body = json.loads(request.content)
        config = body["generationConfig"]
        assert config["responseMimeType"] == "application/json"
        schema = config["responseJsonSchema"]
        assert schema["properties"]["status"]["enum"] == ["need_more_info", "plan_ready"]
        assert schema["$defs"]["GeneratedPlan"]["properties"]["tasks"]["type"] == "array"
        assert schema["$defs"]["GeneratedPlan"]["properties"]["tasks"]["minItems"] == 1
        assert schema["$defs"]["GeneratedPlan"]["properties"]["tasks"]["maxItems"] == 3
        return httpx.Response(200, json={"candidates": [{
            "content": {"parts": [{"text": json.dumps(READY)}], "role": "model"},
            "finishReason": "STOP",
        }]})

    with httpx.Client(transport=httpx.MockTransport(handle)) as http_client:
        with gemini.genai.Client(api_key="test-key", http_options=types.HttpOptions(
            httpx_client=http_client,
        )) as sdk_client:
            monkeypatch.setattr(gemini.genai, "Client", lambda **kwargs: sdk_client)
            response = AIPlannerService(gemini.GeminiPlannerProvider(
                api_key="test-key", model="test-model",
            )).generate_plan(AiPlannerChatRequest(user_prompt="Fitness"))
    assert response.status == "plan_ready"
    assert response.plan.goal_title == "Fitness"
    assert response.plan.tasks[0].title == "Walk"


@pytest.mark.parametrize("payload", [READY, FOLLOW_UP])
def test_valid_structured_output_preserves_api_response_and_history(generate_content, payload):
    response = run_planner(generate_content, json.dumps(payload))
    assert response.status == payload["status"]
    assert response.message == payload["message"]
    assert response.questions == payload["questions"]
    assert response.conversation_history[0].content == "Fitness"
    assert response.conversation_history[-1].role == "assistant"
    if payload["status"] == "plan_ready":
        assert response.plan.tasks[0].title == "Walk"
    else:
        assert response.plan is None


@pytest.mark.parametrize("raw", [
    None, "", "   ", "Not JSON", "[]", "null",
    '```json\n{"status":"need_more_info","message":"Question"}\n```',
    'Here is the result: {"status":"need_more_info","message":"Question"}',
    '{"status":"need_more_info","message":"Question",}',
    '{"status":"need_more_info","message":"Question"} trailing text',
])
def test_malformed_or_non_object_json_is_rejected_without_repair(generate_content, raw):
    with pytest.raises(AIInvalidOutputError):
        run_planner(generate_content, raw)


@pytest.mark.parametrize("number", [float("nan"), float("inf"), float("-inf")], ids=["NaN", "Infinity", "-Infinity"])
def test_non_json_numeric_constants_are_rejected(generate_content, number):
    payload = {**READY, "plan": {"goal_title": "Fitness", "tasks": [{
        "title": "Walk", "schedule_type": "weekly", "schedule_value_json": {"days": [number]},
    }]}}
    with pytest.raises(AIInvalidOutputError):
        run_planner(generate_content, json.dumps(payload))


INVALID_RESULTS = [
    {"status": "plan_ready", "message": "Ready"},
    {**READY, "plan": None},
    {**READY, "plan": {"goal_title": "Fitness", "tasks": []}},
    {**READY, "questions": ["When?"]},
    {**FOLLOW_UP, "plan": VALID_PLAN},
    {"message": "Missing status"},
    {"status": "need_more_info"},
    {**FOLLOW_UP, "status": "unknown"},
    {**FOLLOW_UP, "questions": "When?"},
    {**FOLLOW_UP, "unexpected": "Must not be silently discarded"},
    {**READY, "plan": "not a plan"},
    {**READY, "plan": {"goal_title": "Fitness", "tasks": [{}]}},
    {**READY, "plan": {"goal_title": "Fitness", "tasks": [{
        "title": "Walk", "schedule_type": "monthly", "schedule_value_json": {},
    }]}},
    {**READY, "plan": {"goal_title": "Fitness", "tasks": [{
        "title": "Walk", "schedule_type": "weekly", "schedule_value_json": "invalid",
    }]}},
]


@pytest.mark.parametrize("payload", INVALID_RESULTS)
def test_invalid_structured_result_is_rejected_before_response_mapping(generate_content, payload):
    with pytest.raises(AIInvalidOutputError):
        run_planner(generate_content, json.dumps(payload))


@pytest.mark.parametrize("payload", INVALID_RESULTS[:5])
def test_result_status_invariants_apply_to_any_provider(payload):
    with pytest.raises(ValueError):
        PlannerResult.model_validate(payload)


@pytest.mark.parametrize("count", [0, 1, 2, 3, 4])
def test_generated_task_count_is_enforced_without_silent_truncation(generate_content, count):
    payload = {**READY, "plan": {"goal_title": "Fitness", "tasks": [
        {**VALID_PLAN["tasks"][0], "title": f"Task {i}"} for i in range(count)
    ]}}
    if count in (0, 4):
        with pytest.raises(AIInvalidOutputError):
            run_planner(generate_content, json.dumps(payload))
    else:
        response = run_planner(generate_content, json.dumps(payload))
        assert [task.title for task in response.plan.tasks] == [f"Task {i}" for i in range(count)]


def test_any_provider_rejects_more_than_three_tasks():
    with pytest.raises(ValueError):
        PlannerResult.model_validate({**READY, "plan": {
            "goal_title": "Fitness", "tasks": VALID_PLAN["tasks"] * 4,
        }})
