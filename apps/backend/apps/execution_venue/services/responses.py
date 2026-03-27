from apps.execution_venue.models import VenueOrderPayload, VenueOrderResponse, VenueResponseStatus


def map_error(reason_codes: list[str]) -> str:
    if any(code.endswith('_UNSUPPORTED') for code in reason_codes):
        return VenueResponseStatus.UNSUPPORTED
    if any(code.startswith('MISSING_') for code in reason_codes):
        return VenueResponseStatus.INVALID_PAYLOAD
    return VenueResponseStatus.REJECTED


def map_response(*, valid: bool, reason_codes: list[str], warnings: list[str], payload: VenueOrderPayload) -> tuple[str, str | None, dict]:
    if not valid:
        status = map_error(reason_codes)
        return status, None, {'simulated': True, 'sandbox_only': True}

    if payload.metadata.get('force_manual_confirmation'):
        return VenueResponseStatus.REQUIRES_CONFIRMATION, None, {'simulated': True, 'requires_manual_confirmation': True}

    if payload.quantity <= 0:
        return VenueResponseStatus.INVALID_PAYLOAD, None, {'simulated': True}

    if payload.quantity > 100:
        return VenueResponseStatus.HOLD, None, {'simulated': True, 'risk_hold': 'size_threshold'}

    return VenueResponseStatus.ACCEPTED, f'sbx-{payload.id}', {'simulated': True, 'sandbox_only': True, 'warnings': warnings}


def dry_run(payload: VenueOrderPayload, *, valid: bool, reason_codes: list[str], warnings: list[str], metadata: dict | None = None) -> VenueOrderResponse:
    metadata = metadata or {}
    status, external_order_id, mapped_metadata = map_response(valid=valid, reason_codes=reason_codes, warnings=warnings, payload=payload)
    response = VenueOrderResponse.objects.create(
        intent=payload.intent,
        payload=payload,
        external_order_id=external_order_id,
        normalized_status=status,
        reason_codes=reason_codes,
        warnings=warnings,
        metadata={
            **mapped_metadata,
            **metadata,
        },
    )
    return response
