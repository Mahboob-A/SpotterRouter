"""Domain exceptions for the explanations application."""


class LLMError(Exception):
    """Base exception for all LLM client failures."""


class LLMConfigurationError(LLMError):
    """Raised when required LLM credentials or settings are absent or invalid."""


class LLMServiceError(LLMError):
    """Raised when an external LLM request fails, times out, or returns invalid data."""
