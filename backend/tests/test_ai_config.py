from unittest.mock import Mock

import pytest

from app.ai_planner.providers import gemini
from app.ai_planner.errors import AIConfigurationError
from app.ai_planner.providers.base import PlannerRequest


@pytest.mark.parametrize("api_key,model", [(None, None), (None, "test-model"), ("test-key", None)])
def test_call_ai_rejects_missing_configuration_before_client_creation(
    monkeypatch, api_key, model,
):
    client_mock = Mock()

    monkeypatch.setattr(gemini.genai, "Client", client_mock)

    with pytest.raises(AIConfigurationError):
        gemini.GeminiPlannerProvider(api_key=api_key, model=model).generate_plan(
            PlannerRequest(user_prompt="test prompt"),
        )

    client_mock.assert_not_called()
