from __future__ import annotations

from django.db import transaction

from apps.broker_bridge.models import BrokerBridgeValidation, BrokerIntentStatus, BrokerOrderIntent, BrokerValidationOutcome
from apps.certification_board.models import CertificationLevel, CertificationRun
from apps.incident_commander.models import IncidentRecord, IncidentSeverity, IncidentStatus
from apps.incident_commander.services import get_current_degraded_mode_state
from apps.operator_queue.models import OperatorQueueItem, OperatorQueuePriority, OperatorQueueSource, OperatorQueueType
from apps.runtime_governor.models import RuntimeStateStatus
from apps.runtime_governor.services import get_runtime_state
from apps.safety_guard.models import SafetyStatus
from apps.safety_guard.services.kill_switch import get_or_create_config


def _latest_certification() -> CertificationRun | None:
    return CertificationRun.objects.select_related('operating_envelope').order_by('-created_at', '-id').first()


@transaction.atomic
def validate_intent(*, intent: BrokerOrderIntent, metadata: dict | None = None) -> BrokerBridgeValidation:
    blocking_reasons: list[str] = []
    warnings: list[str] = []
    missing_fields: list[str] = []
    checks: dict = {}

    cert = _latest_certification()
    envelope = cert.operating_envelope if cert else None

    if not cert:
        warnings.append('No certification run found; defaulting to manual review posture.')
    else:
        checks['certification_level'] = cert.certification_level
        if cert.certification_level in {CertificationLevel.NOT_CERTIFIED, CertificationLevel.REMEDIATION_REQUIRED, CertificationLevel.RECERTIFICATION_REQUIRED}:
            blocking_reasons.append(f'Certification level {cert.certification_level} blocks broker routing readiness.')

    runtime = get_runtime_state()
    checks['runtime'] = {'mode': runtime.current_mode, 'status': runtime.status}
    if runtime.status in {RuntimeStateStatus.PAUSED, RuntimeStateStatus.STOPPED}:
        blocking_reasons.append(f'Runtime status is {runtime.status}.')

    safety = get_or_create_config()
    checks['safety'] = {'status': safety.status, 'kill_switch_enabled': safety.kill_switch_enabled, 'hard_stop_active': safety.hard_stop_active}
    if safety.kill_switch_enabled or safety.hard_stop_active or safety.status in {SafetyStatus.HARD_STOP, SafetyStatus.KILL_SWITCH, SafetyStatus.PAUSED}:
        blocking_reasons.append('Safety guard currently blocks new bridge routing attempts.')

    degraded = get_current_degraded_mode_state()
    checks['degraded_mode'] = {'state': degraded.state, 'auto_execution_enabled': degraded.auto_execution_enabled, 'disabled_actions': degraded.disabled_actions}
    if not degraded.auto_execution_enabled:
        blocking_reasons.append('Degraded mode disabled auto execution pathways.')

    critical_incidents = IncidentRecord.objects.filter(status__in=[IncidentStatus.OPEN, IncidentStatus.ESCALATED, IncidentStatus.DEGRADED], severity=IncidentSeverity.CRITICAL).count()
    checks['critical_incidents_open'] = critical_incidents
    if critical_incidents > 0:
        blocking_reasons.append(f'{critical_incidents} critical incident(s) are still open.')

    if envelope:
        checks['operating_envelope'] = {'auto_execution_allowed': envelope.auto_execution_allowed, 'max_autonomy_mode_allowed': envelope.max_autonomy_mode_allowed}
        if not envelope.auto_execution_allowed:
            warnings.append('Operating envelope disallows auto execution; manual review required.')

    if not intent.market_ref:
        missing_fields.append('market_ref')
    if not intent.symbol:
        missing_fields.append('symbol')
    if intent.quantity <= 0:
        blocking_reasons.append('Quantity must be greater than zero.')
    if intent.side not in {'BUY', 'SELL'}:
        blocking_reasons.append('Mapped broker side must be BUY or SELL.')

    requires_manual = bool(warnings or missing_fields)
    is_valid = not blocking_reasons
    if not is_valid:
        outcome = BrokerValidationOutcome.INVALID
        intent.status = BrokerIntentStatus.REJECTED
    elif requires_manual:
        outcome = BrokerValidationOutcome.MANUAL_REVIEW
        intent.status = BrokerIntentStatus.VALIDATED
    else:
        outcome = BrokerValidationOutcome.VALID
        intent.status = BrokerIntentStatus.DRY_RUN_READY

    intent.save(update_fields=['status', 'updated_at'])

    validation = BrokerBridgeValidation.objects.create(
        intent=intent,
        outcome=outcome,
        is_valid=is_valid,
        requires_manual_review=requires_manual,
        blocking_reasons=blocking_reasons,
        warnings=warnings,
        missing_fields=missing_fields,
        checks=checks,
        metadata=metadata or {},
    )

    if outcome in {BrokerValidationOutcome.INVALID, BrokerValidationOutcome.MANUAL_REVIEW}:
        OperatorQueueItem.objects.create(
            status='PENDING',
            source=OperatorQueueSource.SAFETY,
            queue_type=OperatorQueueType.BLOCKED_REVIEW,
            related_market=intent.market,
            priority=OperatorQueuePriority.HIGH if outcome == BrokerValidationOutcome.INVALID else OperatorQueuePriority.MEDIUM,
            headline=f'Broker bridge intent #{intent.id} requires review',
            summary='Broker bridge validation produced blocking reasons or manual review requirements.',
            rationale='; '.join(blocking_reasons or warnings or ['Manual review required by policy posture.']),
            metadata={
                'broker_bridge_intent_id': intent.id,
                'validation_id': validation.id,
                'blocking_reasons': blocking_reasons,
                'warnings': warnings,
                'missing_fields': missing_fields,
            },
        )

    return validation
