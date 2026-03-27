from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError

from apps.broker_bridge.models import BrokerIntentStatus, BrokerOrderIntent
from apps.broker_bridge.services.mapping import map_paper_order, normalize_quantity, pick_mapping_profile
from apps.execution_simulator.models import PaperOrder


def create_intent(*, source_type: str, source_id: int | str | None = None, payload: dict | None = None) -> BrokerOrderIntent:
    data = payload or {}
    source_type = source_type or 'manual'

    if source_type == 'paper_order':
        if not source_id:
            raise ValidationError('source_id is required for source_type=paper_order')
        order = PaperOrder.objects.select_related('market').get(pk=source_id)
        mapping = map_paper_order(order)
        return BrokerOrderIntent.objects.create(
            source_type='paper_order',
            source_id=str(order.id),
            source_ref=f'paper_order:{order.id}',
            related_paper_order=order,
            market=order.market,
            market_ref=mapping.market_ref,
            symbol=mapping.symbol,
            side=mapping.side,
            order_type=mapping.order_type,
            quantity=normalize_quantity(order.remaining_quantity),
            limit_price=order.requested_price,
            time_in_force='GTC',
            mapping_profile=mapping.mapping_profile,
            created_from=order.created_from,
            status=BrokerIntentStatus.DRAFT,
            metadata={
                'paper_order_side': order.side,
                'paper_order_status': order.status,
                'paper_order_id': order.id,
                **(data.get('metadata') or {}),
            },
        )

    quantity = Decimal(str(data.get('quantity') or '0'))
    if quantity <= 0:
        raise ValidationError('quantity must be > 0 for non-paper sources')

    return BrokerOrderIntent.objects.create(
        source_type=source_type,
        source_id=str(source_id or data.get('source_id') or ''),
        source_ref=data.get('source_ref') or f'{source_type}:{source_id or "na"}',
        market_id=data.get('market_id'),
        market_ref=data.get('market_ref', ''),
        symbol=data.get('symbol', ''),
        side=data.get('side', 'BUY'),
        order_type=data.get('order_type', 'market'),
        quantity=normalize_quantity(quantity),
        limit_price=data.get('limit_price'),
        time_in_force=data.get('time_in_force', 'GTC'),
        mapping_profile=data.get('mapping_profile') or pick_mapping_profile(source_type=source_type, created_from=data.get('created_from')),
        created_from=data.get('created_from', 'manual'),
        status=BrokerIntentStatus.DRAFT,
        metadata=data.get('metadata') or {},
    )
