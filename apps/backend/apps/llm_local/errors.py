class LlmLocalError(Exception):
    """Base class for local LLM integration errors."""


class LlmConfigurationError(LlmLocalError):
    """Raised when local LLM configuration is invalid or unsupported."""


class LlmUnavailableError(LlmLocalError):
    """Raised when provider is disabled or unreachable."""


class LlmResponseParseError(LlmLocalError):
    """Raised when structured LLM output cannot be parsed."""
