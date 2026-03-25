from __future__ import annotations

import json
from urllib import error, request

from apps.llm_local.config import get_llm_local_settings
from apps.llm_local.errors import LlmConfigurationError, LlmResponseParseError, LlmUnavailableError


class OllamaEmbeddingClient:
    def __init__(self):
        self.settings = get_llm_local_settings()

    def embed_text(self, text: str) -> list[float]:
        payload = self._embed_request_payload(text)
        result = self._post_embeddings(payload)
        return self._extract_embedding(result)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings = []
        for text in texts:
            embeddings.append(self.embed_text(text))
        return embeddings

    def _embed_request_payload(self, text: str) -> dict:
        if not self.settings.enabled:
            raise LlmUnavailableError('LLM integration is disabled (LLM_ENABLED=false).')
        if self.settings.provider != 'ollama':
            raise LlmConfigurationError(f"Unsupported provider '{self.settings.provider}'.")
        return {'model': self.settings.embed_model, 'prompt': text}

    def _extract_embedding(self, result: dict) -> list[float]:
        vector = result.get('embedding')
        if not isinstance(vector, list) or not vector:
            raise LlmResponseParseError('Embeddings response does not include a valid vector.')
        return [float(item) for item in vector]

    def _post_embeddings(self, payload: dict) -> dict:
        url = f'{self.settings.ollama_base_url}/api/embeddings'
        data = json.dumps(payload).encode('utf-8')
        req = request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')

        try:
            with request.urlopen(req, timeout=self.settings.timeout_seconds) as response:
                body = response.read().decode('utf-8')
        except error.HTTPError as exc:
            raise LlmUnavailableError(f'Ollama HTTP error ({exc.code}) while calling embeddings.') from exc
        except error.URLError as exc:
            raise LlmUnavailableError(f'Ollama connection error while calling embeddings: {exc.reason}') from exc

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise LlmResponseParseError('Embeddings response is not valid JSON.') from exc
        if not isinstance(parsed, dict):
            raise LlmResponseParseError('Embeddings response must be a JSON object.')
        return parsed
