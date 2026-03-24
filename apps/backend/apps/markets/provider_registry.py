from __future__ import annotations

import sys
from pathlib import Path

from django.conf import settings


def _ensure_provider_paths() -> None:
    configured_root = getattr(settings, 'MONOREPO_ROOT', None)
    monorepo_root = Path(configured_root) if configured_root else Path(__file__).resolve().parents[4]
    for relative in ('libs/provider-core', 'libs/provider-kalshi', 'libs/provider-polymarket'):
        path = str((monorepo_root / relative).resolve())
        if path not in sys.path:
            sys.path.insert(0, path)


_ensure_provider_paths()

from provider_kalshi import KalshiReadOnlyClient  # noqa: E402
from provider_polymarket import PolymarketReadOnlyClient  # noqa: E402


def get_provider_client(provider_slug: str):
    normalized = provider_slug.strip().lower()
    if normalized == 'kalshi':
        return KalshiReadOnlyClient()
    if normalized == 'polymarket':
        return PolymarketReadOnlyClient()
    raise ValueError(f'Unsupported read-only provider: {provider_slug}')
