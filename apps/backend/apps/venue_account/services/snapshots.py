from decimal import Decimal

from django.db.models import Sum

from apps.execution_simulator.models import PaperOrderStatus
from apps.execution_venue.models import VenueOrderResponse
from apps.paper_trading.services.portfolio import get_active_account
from apps.venue_account.models import (
    VenueAccountMode,
    VenueAccountSnapshot,
    VenueBalanceSnapshot,
    VenueOrderMirrorStatus,
    VenueOrderSnapshot,
    VenuePositionMirrorStatus,
    VenuePositionSnapshot,
)

VENUE_RESPONSE_TO_ORDER_STATUS = {
    'ACCEPTED': VenueOrderMirrorStatus.OPEN,
    'HOLD': VenueOrderMirrorStatus.OPEN,
    'REQUIRES_CONFIRMATION': VenueOrderMirrorStatus.NEW,
    'REJECTED': VenueOrderMirrorStatus.REJECTED,
    'UNSUPPORTED': VenueOrderMirrorStatus.REJECTED,
    'INVALID_PAYLOAD': VenueOrderMirrorStatus.REJECTED,
}


def build_order_snapshots() -> int:
    responses = VenueOrderResponse.objects.select_related('intent', 'payload', 'intent__related_paper_order').order_by('-created_at', '-id')[:500]
    updated = 0

    for response in responses:
        payload = response.payload
        intent = response.intent
        external_order_id = response.external_order_id or f'sandbox-intent-{intent.id}-response-{response.id}'
        quantity = payload.quantity if payload else intent.quantity

        paper_order = intent.related_paper_order
        filled_quantity = Decimal('0.0000')
        if paper_order:
            filled_quantity = paper_order.fills.aggregate(total=Sum('fill_quantity')).get('total') or Decimal('0.0000')

        status = VENUE_RESPONSE_TO_ORDER_STATUS.get(response.normalized_status, VenueOrderMirrorStatus.NEW)
        if paper_order and paper_order.status == PaperOrderStatus.FILLED:
            status = VenueOrderMirrorStatus.FILLED
        elif paper_order and paper_order.status == PaperOrderStatus.PARTIALLY_FILLED:
            status = VenueOrderMirrorStatus.PARTIALLY_FILLED
        elif paper_order and paper_order.status == PaperOrderStatus.CANCELLED:
            status = VenueOrderMirrorStatus.CANCELLED
        elif paper_order and paper_order.status == PaperOrderStatus.EXPIRED:
            status = VenueOrderMirrorStatus.EXPIRED

        remaining_quantity = max(quantity - filled_quantity, Decimal('0.0000'))

        VenueOrderSnapshot.objects.update_or_create(
            external_order_id=external_order_id,
            defaults={
                'source_intent': intent,
                'source_paper_order': paper_order,
                'source_intent_ref_id': intent.id,
                'instrument_ref': (payload.external_market_id if payload else '') or intent.market_ref or intent.symbol,
                'side': (payload.side if payload else intent.side)[:24],
                'quantity': quantity,
                'filled_quantity': filled_quantity,
                'remaining_quantity': remaining_quantity,
                'status': status,
                'last_response_status': response.normalized_status,
                'metadata': {
                    'response_id': response.id,
                    'payload_id': payload.id if payload else None,
                    'warnings': response.warnings,
                    'reason_codes': response.reason_codes,
                    'sandbox_only': True,
                },
            },
        )
        updated += 1

    return updated


def build_position_snapshots() -> int:
    account = get_active_account()
    positions = account.positions.select_related('market').all()
    updated = 0

    for position in positions:
        status = VenuePositionMirrorStatus.OPEN if position.status == 'OPEN' else VenuePositionMirrorStatus.CLOSED
        VenuePositionSnapshot.objects.update_or_create(
            source_internal_position=position,
            defaults={
                'external_instrument_ref': position.market.slug,
                'side': position.side,
                'quantity': position.quantity,
                'avg_entry_price': position.average_entry_price,
                'unrealized_pnl': position.unrealized_pnl,
                'status': status,
                'metadata': {
                    'paper_market_id': position.market_id,
                    'paper_position_status': position.status,
                    'sandbox_only': True,
                },
            },
        )
        updated += 1

    return updated


def build_account_snapshot() -> VenueAccountSnapshot:
    account = get_active_account()
    open_positions = VenuePositionSnapshot.objects.filter(status=VenuePositionMirrorStatus.OPEN).count()
    open_orders = VenueOrderSnapshot.objects.filter(status__in=[VenueOrderMirrorStatus.NEW, VenueOrderMirrorStatus.OPEN, VenueOrderMirrorStatus.PARTIALLY_FILLED]).count()

    snapshot = VenueAccountSnapshot.objects.create(
        venue_name='sandbox_venue',
        account_reference=f'{account.slug}-sandbox',
        account_mode=VenueAccountMode.SANDBOX_ONLY,
        equity=account.equity,
        cash_available=account.cash_balance,
        reserved_cash=account.reserved_balance,
        open_positions_count=open_positions,
        open_orders_count=open_orders,
        metadata={
            'paper_account_id': account.id,
            'paper_currency': account.currency,
            'sandbox_only': True,
        },
    )

    VenueBalanceSnapshot.objects.create(
        account_snapshot=snapshot,
        currency=account.currency,
        available=account.cash_balance,
        reserved=account.reserved_balance,
        total=account.cash_balance + account.reserved_balance,
        metadata={'source': 'paper_account', 'sandbox_only': True},
    )
    return snapshot
