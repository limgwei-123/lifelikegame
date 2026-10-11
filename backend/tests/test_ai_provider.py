from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.ai_planner.schemas import AiPlannerChatRequest, ConversationMessage
from app.ai_planner.service import AIPlannerService


def test_service_can_use_a_provider_without_vendor_sdk_calls():
    from app.ai_planner.providers.base import PlannerRequest, PlannerResult

    class Planner:
        def generate_plan(self, request):
            assert isinstance(request, PlannerRequest)
            assert request.user_prompt == "Build a habit"
            assert request.conversation_history == [ConversationMessage(role="user", content="Earlier")]
            return PlannerResult(status="need_more_info", message="Tell me more", questions=["When?"])

    payload = AiPlannerChatRequest(
        user_prompt="Build a habit",
        conversation_history=[ConversationMessage(role="user", content="Earlier")],
    )
    response = AIPlannerService(Planner()).generate_plan(payload)
    assert response.status == "need_more_info"
    assert response.questions == ["When?"]
    assert [message.role for message in response.conversation_history] == ["user", "user", "assistant"]
    assert response.conversation_history[-1].content == "Tell me more\nQuestion: \n1. When?"
    assert len(payload.conversation_history) == 1


def test_ready_plan_is_mapped_to_existing_response_and_history():
    from app.ai_planner.providers.base import PlannerResult

    class Planner:
        def generate_plan(self, request):
            return PlannerResult(status="plan_ready", message="Ready", plan={
                "goal_title": "Fitness", "tasks": [{
                    "title": "Walk", "schedule_type": "daily", "schedule_value_json": {},
                }],
            })

    response = AIPlannerService(Planner()).generate_plan(AiPlannerChatRequest(user_prompt="Fitness"))
    assert response.model_dump(exclude={"conversation_history"}) == {
        "draft_id": None,
        "status": "plan_ready", "message": "Ready", "questions": [], "plan": {
            "goal_title": "Fitness", "tasks": [{
                "title": "Walk", "description": None,
                "schedule_type": "daily", "schedule_value_json": {},
            }],
        },
    }
    assert "1. Walk" in response.conversation_history[-1].content


def test_provider_errors_are_not_swallowed():
    class Planner:
        def generate_plan(self, request):
            raise RuntimeError("provider unavailable")

    with pytest.raises(RuntimeError, match="provider unavailable"):
        AIPlannerService(Planner()).generate_plan(AiPlannerChatRequest(user_prompt="Fitness"))


@pytest.mark.parametrize("schedule_type,value,want", [
    ("daily", {"days": [2]}, {}),
    ("weekly", {}, {"days": [1, 3, 5]}),
    ("weekly", {"days": [2, 4]}, {"days": [2, 4]}),
])
def test_gemini_adapter_preserves_prompt_and_schedule_defaults(monkeypatch, schedule_type, value, want):
    import json
    from app.ai_planner.providers import gemini
    from app.ai_planner.providers.base import PlannerRequest

    generate = Mock(return_value=SimpleNamespace(text=json.dumps({
        "status": "plan_ready", "message": "Ready", "plan": {
            "goal_title": "Fitness", "tasks": [{
                "title": "Walk", "schedule_type": schedule_type, "schedule_value_json": value,
            }],
        },
    })))
    monkeypatch.setattr(gemini.genai, "Client", lambda **kwargs: SimpleNamespace(
        models=SimpleNamespace(generate_content=generate), close=Mock(),
    ))
    request = PlannerRequest(user_prompt="Fitness", conversation_history=[])
    result = gemini.GeminiPlannerProvider(api_key="test-key", model="test-model").generate_plan(request)
    assert result.plan.tasks[0].schedule_value_json == want
    assert generate.call_args.kwargs["model"] == "test-model"
    assert "Fitness" in generate.call_args.kwargs["contents"]
    assert "No previous conversation." in generate.call_args.kwargs["contents"]


def test_service_factory_injects_selected_provider(monkeypatch):
    from app.ai_planner import dependencies
    from app.ai_planner.providers.base import PlannerResult

    class Planner:
        def generate_plan(self, request):
            return PlannerResult(status="need_more_info", message="Injected")

    monkeypatch.setattr(dependencies, "build_ai_planner_provider", lambda: Planner())
    response = dependencies.build_ai_planner_service().generate_plan(AiPlannerChatRequest(user_prompt="Hi"))
    assert response.message == "Injected"


def test_http_endpoint_uses_provider_and_preserves_response(client, auth_headers, monkeypatch):
    from app.ai_planner import dependencies
    from app.ai_planner.providers.base import PlannerResult

    class Planner:
        def __init__(self, before_send, observation=None):
            self.before_send = before_send

        def generate_plan(self, request):
            self.before_send()
            assert request.user_prompt == "Fitness"
            return PlannerResult(status="need_more_info", message="When?", questions=["Which days?"])

    monkeypatch.setattr(dependencies, "build_ai_planner_provider", lambda **kwargs: Planner(**kwargs))
    response = client.post(
        "/ai-planner/generate-plan", headers=auth_headers, json={"user_prompt": "Fitness"},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {
        "draft_id": None,
        "status": "need_more_info", "message": "When?", "questions": ["Which days?"],
        "plan": None, "conversation_history": [
            {"role": "user", "content": "Fitness"},
            {"role": "assistant", "content": "When?\nQuestion: \n1. Which days?"},
        ],
    }


def test_core_can_import_and_run_without_gemini_sdk():
    from pathlib import Path
    import subprocess
    import sys

    result = subprocess.run([sys.executable, "-c", '''
import builtins
original_import = builtins.__import__
def guarded_import(name, *args, **kwargs):
    if name == "google" or name.startswith("google.genai"):
        raise ImportError("Vendor SDK must not be imported by planner core")
    return original_import(name, *args, **kwargs)
builtins.__import__ = guarded_import
from app.ai_planner.service import AIPlannerService
from app.ai_planner.providers.base import PlannerRequest, PlannerResult
from app.ai_planner.schemas import AiPlannerChatRequest
class Planner:
    def generate_plan(self, request):
        return PlannerResult(status="need_more_info", message="Independent")
assert AIPlannerService(Planner()).generate_plan(AiPlannerChatRequest(user_prompt="Hi")).message == "Independent"
'''], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("configured_provider", [None, "gemini"])
def test_factory_uses_gemini_with_legacy_or_explicit_environment(monkeypatch, configured_provider):
    import json
    from app.ai_planner import dependencies
    from app.ai_planner.providers import gemini
    from app.core.config import Settings

    if configured_provider is None:
        monkeypatch.delenv("AI_PROVIDER", raising=False)
    else:
        monkeypatch.setenv("AI_PROVIDER", configured_provider)
    monkeypatch.setenv("AI_API_KEY", "configured-key")
    monkeypatch.setenv("AI_MODEL", "configured-model")
    settings = Settings(_env_file=None)
    monkeypatch.setattr(dependencies, "get_settings", lambda: settings)
    generate = Mock(return_value=SimpleNamespace(text=json.dumps({
        "status": "need_more_info", "message": "Configured Gemini", "questions": ["When?"],
    })))
    client = Mock(return_value=SimpleNamespace(models=SimpleNamespace(generate_content=generate), close=Mock()))
    monkeypatch.setattr(gemini.genai, "Client", client)

    response = dependencies.build_ai_planner_service().generate_plan(AiPlannerChatRequest(user_prompt="Fitness"))

    assert response.message == "Configured Gemini"
    assert response.questions == ["When?"]
    assert response.conversation_history[-1].role == "assistant"
    assert client.call_args.kwargs["api_key"] == "configured-key"
    assert generate.call_args.kwargs["model"] == "configured-model"


@pytest.mark.parametrize("provider", ["unknown", "ollama", "", "GEMINI"])
def test_factory_rejects_unsupported_provider_without_calling_gemini(monkeypatch, provider):
    from app.ai_planner import dependencies
    from app.ai_planner.errors import AIConfigurationError
    from app.ai_planner.providers import gemini
    from app.core.config import Settings

    monkeypatch.setenv("AI_PROVIDER", provider)
    settings = Settings(_env_file=None, ai_api_key="configured-key", ai_model="configured-model")
    monkeypatch.setattr(dependencies, "get_settings", lambda: settings)
    client = Mock(side_effect=AssertionError("Unsupported providers must not call Gemini"))
    monkeypatch.setattr(gemini.genai, "Client", client)

    with pytest.raises(AIConfigurationError):
        dependencies.build_ai_planner_service().generate_plan(AiPlannerChatRequest(user_prompt="Fitness"))
    client.assert_not_called()
