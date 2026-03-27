from decimal import Decimal

from apps.broker_bridge.models import BrokerOrderIntent
from apps.execution_venue.models import VenueCapabilityProfile, VenueOrderPayload

ORDER_TYPE_MAP = {
    'market': 'market_like',
    'market_like': 'market_like',
    'limit': 'limit_like',
    'limit_like': 'limit_like',
    'close_order': 'close_order',
}


def _to_external_market_id(intent: BrokerOrderIntent) -> str:
    if intent.symbol:
        return intent.symbol
    if intent.market_ref:
        return intent.market_ref
    if intent.market_id:
        return f'market:{intent.market_id}'
    return ''


def build_payload(intent: BrokerOrderIntent, capability: VenueCapabilityProfile, metadata: dict | None = None) -> VenueOrderPayload:
    metadata = metadata or {}
    normalized_order_type = ORDER_TYPE_MAP.get(intent.order_type, intent.order_type or 'market_like')
    tif = intent.time_in_force or ''
    reduce_only = intent.side in {'REDUCE'}
    close_flag = intent.side in {'CLOSE'} or normalized_order_type == 'close_order'

    payload = VenueOrderPayload.objects.create(
        intent=intent,
        venue_name=capability.venue_name,
        external_market_id=_to_external_market_id(intent),
        side=intent.side,
        order_type=normalized_order_type,
        quantity=Decimal(intent.quantity),
        limit_price=intent.limit_price,
        tif=tif,
        reduce_only=reduce_only,
        close_flag=close_flag,
        source_intent_id=intent.id,
        metadata={
            'source_type': intent.source_type,
            'mapping_profile': intent.mapping_profile,
            'sandbox_only': True,
            **metadata,
        },
    )
    return payload


def validate_payload(payload: VenueOrderPayload, capability: VenueCapabilityProfile) -> tuple[bool, list[str], list[str], list[str]]:
    reason_codes: list[str] = []
    warnings: list[str] = []
    missing_fields: list[str] = []

    if not payload.external_market_id:
        missing_fields.append('external_market_id')
        reason_codes.append('MISSING_EXTERNAL_MARKET_ID')

    if payload.order_type == 'market_like' and not capability.supports_market_like:
        reason_codes.append('MARKET_ORDER_UNSUPPORTED')
    if payload.order_type == 'limit_like' and not capability.supports_limit_like:
        reason_codes.append('LIMIT_ORDER_UNSUPPORTED')
    if payload.order_type == 'close_order' and not capability.supports_close_order:
        reason_codes.append('CLOSE_ORDER_UNSUPPORTED')

    if payload.reduce_only and not capability.supports_reduce_only:
        reason_codes.append('REDUCE_ONLY_UNSUPPORTED')

    if payload.order_type == 'limit_like' and payload.limit_price is None:
        missing_fields.append('limit_price')
        reason_codes.append('MISSING_LIMIT_PRICE')

    if capability.requires_symbol_mapping and not payload.external_market_id:
        warnings.append('symbol_mapping_required_before_live')

    is_valid = len(reason_codes) == 0
    return is_valid, reason_codes, warnings, missing_fields
