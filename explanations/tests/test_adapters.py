from unittest.mock import MagicMock, patch

import pytest
import requests

from explanations.adapters import (
    FireworksLLMClient,
    LLMClient,
    resolve_fireworks_model,
)
from explanations.exceptions import (
    LLMConfigurationError,
    LLMServiceError,
)


def test_resolve_fireworks_model_prioritizes_typo_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FIREWORKS_LLM_MODEL_NAE", "custom/typo-model")
    monkeypatch.setenv("FIREWORKS_LLM_MODEL_NAME", "custom/correct-model")
    assert resolve_fireworks_model() == "custom/typo-model"


def test_resolve_fireworks_model_falls_back_to_model_name_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FIREWORKS_LLM_MODEL_NAE", raising=False)
    monkeypatch.setenv("FIREWORKS_LLM_MODEL_NAME", "custom/correct-model")
    assert resolve_fireworks_model() == "custom/correct-model"


def test_resolve_fireworks_model_defaults_to_deepseek_v4p1_flash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FIREWORKS_LLM_MODEL_NAE", raising=False)
    monkeypatch.delenv("FIREWORKS_LLM_MODEL_NAME", raising=False)
    assert (
        resolve_fireworks_model()
        == "accounts/fireworks/models/deepseek-v4p1-flash"
    )


def test_fireworks_client_implements_llm_client_interface() -> None:
    client = FireworksLLMClient(api_key="dummy-key")
    assert isinstance(client, LLMClient)


def test_fireworks_client_raises_configuration_error_when_key_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    client = FireworksLLMClient(api_key="")
    with pytest.raises(LLMConfigurationError, match="API key"):
        client.generate_explanation("Explain this route")


@patch("requests.post")
def test_fireworks_client_success(mock_post: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "cmpl-123",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Selected stop 1 in Effingham due to low $2.85 price.",
                },
                "finish_reason": "stop",
            }
        ],
    }
    mock_post.return_value = mock_response

    client = FireworksLLMClient(
        api_key="test-api-key",
        model="accounts/fireworks/models/deepseek-v4p1-flash",
    )
    result = client.generate_explanation(
        prompt="Route has 1 stop",
        system_prompt="Custom system prompt",
    )

    assert result == "Selected stop 1 in Effingham due to low $2.85 price."
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["headers"]["Authorization"] == "Bearer test-api-key"
    assert call_kwargs["headers"]["Content-Type"] == "application/json"
    assert (
        call_kwargs["json"]["model"]
        == "accounts/fireworks/models/deepseek-v4p1-flash"
    )
    assert call_kwargs["json"]["messages"] == [
        {"role": "system", "content": "Custom system prompt"},
        {"role": "user", "content": "Route has 1 stop"},
    ]
    assert call_kwargs["json"]["temperature"] == 0.2
    assert call_kwargs["json"]["max_tokens"] == 1200


@patch("requests.post")
def test_fireworks_client_http_error(mock_post: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_post.return_value = mock_response

    client = FireworksLLMClient(api_key="invalid-key")
    with pytest.raises(LLMServiceError, match="status 401"):
        client.generate_explanation("Route summary")


@patch("requests.post")
def test_fireworks_client_timeout_error(mock_post: MagicMock) -> None:
    mock_post.side_effect = requests.Timeout("Connection timed out")

    client = FireworksLLMClient(api_key="test-key", timeout_seconds=2.0)
    with pytest.raises(LLMServiceError, match="timed out"):
        client.generate_explanation("Route summary")


@patch("requests.post")
def test_fireworks_client_malformed_response_json(mock_post: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"error": "unexpected format"}
    mock_post.return_value = mock_response

    client = FireworksLLMClient(api_key="test-key")
    with pytest.raises(LLMServiceError, match="Malformed response"):
        client.generate_explanation("Route summary")
