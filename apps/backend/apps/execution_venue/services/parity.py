from django.db import transaction
from django.utils import timezone

from apps.broker_bridge.models import BrokerOrderIntent
from apps.execution_venue.models import VenueParityRun, VenueParityStatus
from apps.execution_venue.services.adapters import NullSandboxVenueAdapter
from apps.incident_commander.models import IncidentRecord, IncidentSeverity, IncidentStatus, IncidentType


@transaction.atomic
def run_parity(intent: BrokerOrderIntent, metadata: dict | None = None) -> VenueParityRun:
    metadata = metadata or {}
    adapter = NullSandboxVenueAdapter()

    payload = adapter.build_payload(intent=intent, metadata={'triggered_from': 'execution_venue_parity', **metadata})
    valid, reason_codes, warnings, missing_fields = adapter.validate_payload(payload)
    response = adapter.dry_run(payload=payload, metadata={'triggered_from': 'execution_venue_parity', **metadata})

    latest_dry_run = intent.dry_runs.order_by('-created_at', '-id').first()
    simulator_order = intent.related_paper_order

    issues: list[str] = []
    unsupported_actions: list[str] = []

    if not valid:
        issues.extend(reason_codes)
    if response.normalized_status == 'UNSUPPORTED':
        unsupported_actions.extend(reason_codes)
    if latest_dry_run and latest_dry_run.simulated_response == 'accepted' and response.normalized_status in {'REJECTED', 'UNSUPPORTED', 'INVALID_PAYLOAD'}:
        issues.append('dry_run_vs_venue_mismatch')

    if simulator_order and str(simulator_order.requested_quantity) != str(payload.quantity):
        issues.append('quantity_mismatch_with_execution_simulator')

    readiness_score = max(0, 100 - (len(issues) * 25) - (len(missing_fields) * 20) - (len(unsupported_actions) * 20))
    parity_status = VenueParityStatus.PARITY_OK if not issues and not missing_fields and not unsupported_actions else VenueParityStatus.PARITY_GAP

    run = VenueParityRun.objects.create(
        intent=intent,
        payload=payload,
        response=response,
        parity_status=parity_status,
        issues=issues,
        missing_fields=missing_fields,
        unsupported_actions=unsupported_actions,
        readiness_score=readiness_score,
        bridge_dry_run_id=latest_dry_run.id if latest_dry_run else None,
        simulator_order_id=simulator_order.id if simulator_order else None,
        metadata={
            'warnings': warnings,
            'reason_codes': reason_codes,
            'sandbox_only': True,
            **metadata,
        },
    )

    if parity_status == VenueParityStatus.PARITY_GAP and len(issues) >= 2:
        IncidentRecord.objects.create(
            incident_type=IncidentType.EXECUTION_ANOMALY,
            severity=IncidentSeverity.WARNING,
            status=IncidentStatus.OPEN,
            title='Execution venue parity gap detected',
            summary='Sandbox venue parity run detected multi-factor mapping or semantic gaps.',
            source_app='execution_venue',
            related_object_type='broker_intent',
            related_object_id=str(intent.id),
            first_seen_at=timezone.now(),
            last_seen_at=timezone.now(),
            dedupe_key=f'execution-venue-parity-intent-{intent.id}',
            metadata={
                'parity_run_id': run.id,
                'issues': issues,
                'missing_fields': missing_fields,
                'unsupported_actions': unsupported_actions,
            },
        )

    return run


def build_summary() -> dict:
    runs = VenueParityRun.objects.all()
    total = runs.count()
    parity_ok = runs.filter(parity_status=VenueParityStatus.PARITY_OK).count()
    parity_gap = runs.filter(parity_status=VenueParityStatus.PARITY_GAP).count()
    avg_readiness = round(sum((run.readiness_score for run in runs[:100]), 0) / max(min(total, 100), 1), 2) if total else 0

    latest_run = runs.order_by('-created_at', '-id').first()
    return {
        'adapter': 'null_sandbox',
        'sandbox_only': True,
        'total_runs': total,
        'parity_ok': parity_ok,
        'parity_gap': parity_gap,
        'avg_readiness_score': avg_readiness,
        'latest_run_id': latest_run.id if latest_run else None,
        'latest_parity_status': latest_run.parity_status if latest_run else None,
    }
