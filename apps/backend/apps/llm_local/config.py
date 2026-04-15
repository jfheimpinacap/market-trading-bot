from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class LlmLocalSettings:
    enabled: bool
    provider: str
    ollama_base_url: str
    chat_model: str
    embed_model: str
    timeout_seconds: int


DEFAULT_CHAT_MODEL = 'llama3.2:3b'
DEFAULT_EMBED_MODEL = 'nomic-embed-text'
DEFAULT_TIMEOUT_SECONDS = 30


def get_llm_local_settings() -> LlmLocalSettings:
    timeout_seconds = max(int(getattr(settings, 'OLLAMA_TIMEOUT_SECONDS', DEFAULT_TIMEOUT_SECONDS)), 1)
    enabled = bool(getattr(settings, 'OLLAMA_ENABLED', getattr(settings, 'LLM_ENABLED', False)))
    chat_model = str(getattr(settings, 'OLLAMA_MODEL', getattr(settings, 'OLLAMA_CHAT_MODEL', DEFAULT_CHAT_MODEL)))
    return LlmLocalSettings(
        enabled=enabled,
        provider=str(getattr(settings, 'LLM_PROVIDER', 'ollama')),
        ollama_base_url=str(getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')).rstrip('/'),
        chat_model=chat_model,
        embed_model=str(getattr(settings, 'OLLAMA_EMBED_MODEL', DEFAULT_EMBED_MODEL)),
        timeout_seconds=timeout_seconds,
    )
