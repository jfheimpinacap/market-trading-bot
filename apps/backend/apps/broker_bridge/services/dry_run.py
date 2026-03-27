from __future__ import annotations

from apps.broker_bridge.models import BrokerBridgeValidation, BrokerDryRun, BrokerDryRunResponse, BrokerIntentStatus, BrokerOrderIntent


def run_dry_run(*, intent: BrokerOrderIntent, metadata: dict | None = None) -> BrokerDryRun:
    validation = intent.validations.order_by('-created_at', '-id').first()
    if validation is None:
        validation = BrokerBridgeValidation.objects.create(
            intent=intent,
            outcome='INVALID',
            is_valid=False,
            requires_manual_review=True,
            blocking_reasons=['Intent must be validated before dry-run.'],
            warnings=[],
            missing_fields=[],
            checks={'system': 'validation_missing'},
            metadata={'auto_created': True},
        )

    if not validation.is_valid:
        response = BrokerDryRunResponse.REJECTED
        summary = 'Rejected in dry-run because validation is invalid.'
    elif validation.requires_manual_review:
        response = BrokerDryRunResponse.NEEDS_MANUAL_REVIEW
        summary = 'Dry-run routed to manual review due to warnings/missing fields.'
    elif intent.status == BrokerIntentStatus.DRY_RUN_READY:
        response = BrokerDryRunResponse.ACCEPTED
        summary = 'Dry-run accepted; payload is ready for a future real broker adapter.'
    else:
        response = BrokerDryRunResponse.HOLD
        summary = 'Dry-run put on hold because intent is not in DRY_RUN_READY status.'

    dry_run = BrokerDryRun.objects.create(
        intent=intent,
        validation=validation,
        simulated_response=response,
        dry_run_summary=summary,
        simulated_payload={
            'symbol': intent.symbol,
            'market_ref': intent.market_ref,
            'side': intent.side,
            'type': intent.order_type,
            'quantity': str(intent.quantity),
            'limit_price': str(intent.limit_price) if intent.limit_price is not None else None,
            'time_in_force': intent.time_in_force,
            'mapping_profile': intent.mapping_profile,
        },
        simulated_broker_response={
            'status': response,
            'broker_order_id': f'dryrun-{intent.id}-{intent.dry_runs.count() + 1}',
            'message': summary,
        },
        metadata=metadata or {},
    )

    intent.status = BrokerIntentStatus.DRY_RUN_EXECUTED
    intent.save(update_fields=['status', 'updated_at'])
    return dry_run
