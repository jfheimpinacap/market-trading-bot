from __future__ import annotations

import json
import logging
from urllib import error, request

from apps.llm_local.config import get_llm_local_settings
from apps.llm_local.errors import LlmConfigurationError, LlmResponseParseError, LlmUnavailableError

logger = logging.getLogger(__name__)


class OllamaChatClient:
    def __init__(self):
        self.settings = get_llm_local_settings()

    def status(self) -> dict:
        if not self.settings.enabled:
            return {'reachable': False, 'status': 'disabled', 'message': 'LLM integration is disabled by configuration.'}

        if self.settings.provider != 'ollama':
            return {'reachable': False, 'status': 'unsupported', 'message': f"Unsupported LLM_PROVIDER '{self.settings.provider}'."}

        url = f'{self.settings.ollama_base_url}/api/tags'
        try:
            with request.urlopen(url, timeout=self.settings.timeout_seconds):
                return {'reachable': True, 'status': 'ok', 'message': 'Ollama is reachable.'}
        except Exception as exc:
            logger.warning('Ollama status check failed: %s', exc)
            return {'reachable': False, 'status': 'unreachable', 'message': f'Ollama is not reachable: {exc}'}

    def chat_json(self, *, system_prompt: str, user_prompt: str, schema_hint: str) -> dict:
        if not self.settings.enabled:
            raise LlmUnavailableError('LLM integration is disabled (LLM_ENABLED=false).')
        if self.settings.provider != 'ollama':
            raise LlmConfigurationError(f"Unsupported provider '{self.settings.provider}'.")

        payload = {
            'model': self.settings.chat_model,
            'stream': False,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            'format': 'json',
            'options': {'temperature': 0.2},
        }

        response_payload = self._post_json('/api/chat', payload)
        message = ((response_payload.get('message') or {}).get('content') or '').strip()
        if not message:
            raise LlmResponseParseError('Ollama chat returned an empty response.')

        try:
            parsed = json.loads(message)
        except json.JSONDecodeError as exc:
            raise LlmResponseParseError(f'LLM response is not valid JSON for schema {schema_hint}.') from exc

        if not isinstance(parsed, dict):
            raise LlmResponseParseError(f'LLM response must be a JSON object for schema {schema_hint}.')
        return parsed

    def _post_json(self, endpoint: str, payload: dict) -> dict:
        url = f'{self.settings.ollama_base_url}{endpoint}'
        data = json.dumps(payload).encode('utf-8')
        req = request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')

        try:
            with request.urlopen(req, timeout=self.settings.timeout_seconds) as response:
                body = response.read().decode('utf-8')
        except error.HTTPError as exc:
            body = exc.read().decode('utf-8', errors='ignore')
            logger.warning('Ollama HTTP error on %s: %s', endpoint, body)
            raise LlmUnavailableError(f'Ollama HTTP error ({exc.code}) while calling {endpoint}.') from exc
        except error.URLError as exc:
            raise LlmUnavailableError(f'Ollama connection error while calling {endpoint}: {exc.reason}') from exc

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise LlmResponseParseError(f'Ollama response on {endpoint} is not valid JSON.') from exc

        if not isinstance(parsed, dict):
            raise LlmResponseParseError(f'Ollama response on {endpoint} must be an object.')
        return parsed
