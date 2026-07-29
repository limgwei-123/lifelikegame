from unittest.mock import Mock

import pytest

from app.ai_planner import nodes


def test_call_ai_rejects_missing_configuration_before_client_creation(
    monkeypatch,
):
    client_mock = Mock()

    monkeypatch.setattr(nodes, "api_key", None)
    monkeypatch.setattr(nodes, "model", None)
    monkeypatch.setattr(nodes.genai, "Client", client_mock)

    with pytest.raises(
        RuntimeError,
        match="AI_API_KEY and AI_MODEL",
    ):
        nodes.call_ai("test prompt")

    client_mock.assert_not_called()
