from apps.llm_local.clients import OllamaChatClient
from apps.llm_local.config import get_llm_local_settings


def build_llm_status() -> dict:
    config = get_llm_local_settings()
    status = OllamaChatClient().status()
    return {
        'enabled': config.enabled,
        'provider': config.provider,
        'ollama_base_url': config.ollama_base_url,
        'chat_model': config.chat_model,
        'embed_model': config.embed_model,
        'timeout_seconds': config.timeout_seconds,
        'reachable': status['reachable'],
        'status': status['status'],
        'message': status['message'],
    }
