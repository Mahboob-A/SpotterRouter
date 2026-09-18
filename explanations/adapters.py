"""LLM adapter interfaces and concrete Fireworks AI implementation."""

import os
from abc import ABC, abstractmethod
from typing import Any

import requests
from django.conf import settings

from explanations.exceptions import LLMConfigurationError, LLMServiceError

DEFAULT_FIREWORKS_MODEL = "accounts/fireworks/models/deepseek-v4p1-flash"
DEFAULT_FIREWORKS_URL = "https://api.fireworks.ai/inference/v1/chat/completions"


def resolve_fireworks_model() -> str:
    """Resolve model name defensively checking typo env var first."""
    typo_model = os.environ.get("FIREWORKS_LLM_MODEL_NAE")
    if typo_model and typo_model.strip():
        return typo_model.strip()

    proper_model = os.environ.get("FIREWORKS_LLM_MODEL_NAME")
    if proper_model and proper_model.strip():
        return proper_model.strip()

    settings_model = getattr(settings, "FIREWORKS_LLM_MODEL_NAME", None)
    if settings_model and isinstance(settings_model, str) and settings_model.strip():
        return str(settings_model).strip()

    return DEFAULT_FIREWORKS_MODEL


class LLMClient(ABC):
    """Abstract interface for large language model completion providers."""

    @abstractmethod
    def generate_explanation(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """Generate a plain-language explanation string from the given prompt."""


class FireworksLLMClient(LLMClient):
    """Fireworks AI chat completions adapter for DeepSeek V4.1 Flash."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        configured_key = getattr(
            settings,
            "FIREWORKS_API_KEY",
            os.environ.get("FIREWORKS_API_KEY", ""),
        )
        self.api_key: str = str(api_key if api_key is not None else configured_key)
        self.model: str = model or resolve_fireworks_model()
        configured_url = getattr(
            settings,
            "FIREWORKS_API_BASE_URL",
            os.environ.get("FIREWORKS_API_BASE_URL", DEFAULT_FIREWORKS_URL),
        )
        self.base_url: str = str(base_url or configured_url)
        self.timeout_seconds = timeout_seconds

    def generate_explanation(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """Submit chat completion request to Fireworks AI and extract response."""
        if not self.api_key or not self.api_key.strip():
            raise LLMConfigurationError("Fireworks API key is not configured")

        sys_content = (
            system_prompt
            if system_prompt and system_prompt.strip()
            else "You are an AI assistant that explains fuel stop routing decisions."
        )

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": sys_content},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 500,
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key.strip()}",
        }

        try:
            response = requests.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=self.timeout_seconds,
            )
        except requests.Timeout as exc:
            raise LLMServiceError(
                f"Fireworks API request timed out after {self.timeout_seconds}s"
            ) from exc
        except requests.RequestException as exc:
            raise LLMServiceError(
                f"Fireworks API network error: {exc}"
            ) from exc

        if response.status_code != 200:
            raise LLMServiceError(
                f"Fireworks API returned error status {response.status_code}: "
                f"{response.text[:200]}"
            )

        try:
            data = response.json()
            choices = data.get("choices", [])
            if not choices or not isinstance(choices, list):
                raise LLMServiceError("Malformed response: missing 'choices' list")
            first_choice = choices[0]
            if not isinstance(first_choice, dict):
                raise LLMServiceError("Malformed response: invalid choice element")
            message = first_choice.get("message", {})
            if not isinstance(message, dict):
                raise LLMServiceError("Malformed response: invalid message element")
            content = message.get("content")
            if not isinstance(content, str):
                raise LLMServiceError("Malformed response: missing 'content' string")
            return str(content).strip()
        except (ValueError, KeyError, IndexError) as exc:
            if isinstance(exc, LLMServiceError):
                raise
            raise LLMServiceError(f"Malformed response payload: {exc}") from exc
