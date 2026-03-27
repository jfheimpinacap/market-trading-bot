from __future__ import annotations

from decimal import Decimal

from django.utils import timezone

from apps.execution_simulator.models import (
    PaperOrder,
    PaperOrderCreatedFrom,
    PaperOrderStatus,
)
from apps.execution_simulator.services.policies import get_policy
from apps.paper_trading.services.portfolio import get_active_account


def create_order(
    *,
    market,
    side: str,
    requested_quantity: Decimal,
    order_type: str = 'market_like',
    requested_price: Decimal | None = None,
    created_from: str = PaperOrderCreatedFrom.MANUAL,
    paper_account=None,
    metadata: dict | None = None,
    policy_profile: str | None = None,
) -> PaperOrder:
    account = paper_account or get_active_account()
    policy = get_policy(policy_profile)
    metadata = metadata or {}

    order = PaperOrder.objects.create(
        paper_account=account,
        market=market,
        side=side,
        requested_quantity=requested_quantity,
        remaining_quantity=requested_quantity,
        order_type=order_type,
        requested_price=requested_price,
        created_from=created_from,
        status=PaperOrderStatus.OPEN,
        max_wait_cycles=metadata.get('max_wait_cycles', policy.max_wait_cycles),
        cancel_after_n_cycles=metadata.get('cancel_after_n_cycles', policy.cancel_after_n_cycles),
        expires_at=metadata.get('expires_at'),
        metadata={
            **metadata,
            'policy_profile': policy.slug,
            'paper_demo_only': True,
            'real_execution_enabled': False,
            'created_at_iso': timezone.now().isoformat(),
        },
    )
    return order
