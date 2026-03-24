from __future__ import annotations

from abc import ABC, abstractmethod

from .types import NormalizedMarketRecord


class ReadOnlyProviderClient(ABC):
    provider_slug: str

    @abstractmethod
    def list_markets(
        self,
        *,
        limit: int = 50,
        active_only: bool = False,
        query: str | None = None,
        provider_market_id: str | None = None,
    ) -> list[NormalizedMarketRecord]:
        """Return normalized provider markets using public read-only endpoints."""

    @abstractmethod
    def get_market(self, provider_market_id: str) -> NormalizedMarketRecord:
        """Return one normalized provider market by id."""
