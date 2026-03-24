from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ProviderHttpError(RuntimeError):
    pass


def get_json(base_url: str, path: str, params: dict[str, str | int | bool] | None = None, timeout: float = 15.0):
    query = ''
    if params:
        query = urlencode({k: v for k, v in params.items() if v is not None})
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    if query:
        url = f'{url}?{query}'

    request = Request(url, headers={'Accept': 'application/json', 'User-Agent': 'market-trading-bot-readonly/1.0'})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read().decode('utf-8')
            return json.loads(payload) if payload else {}
    except Exception as exc:
        raise ProviderHttpError(f'HTTP read-only request failed: {url}: {exc}') from exc
