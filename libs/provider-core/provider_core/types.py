from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass(slots=True)
class NormalizedMarketRecord:
    provider_name: str
    provider_slug: str
    provider_market_id: str
    provider_event_id: str | None = None
    title: str = ''
    category: str = ''
    status: str = 'open'
    url: str = ''
    is_active: bool = True
    market_probability: Decimal | None = None
    yes_price: Decimal | None = None
    no_price: Decimal | None = None
    liquidity: Decimal | None = None
    volume: Decimal | None = None
    volume_24h: Decimal | None = None
    close_time: datetime | None = None
    resolution_time: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    event_title: str | None = None
    event_metadata: dict[str, Any] = field(default_factory=dict)
