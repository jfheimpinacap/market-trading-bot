from decimal import Decimal

from apps.broker_bridge.models import BrokerDryRun, BrokerDryRunResponse
from apps.certification_board.models import CertificationLevel, CertificationRun
from apps.chaos_lab.models import ResilienceBenchmark
from apps.incident_commander.models import IncidentRecord, IncidentSeverity, IncidentStatus
from apps.runtime_governor.models import RuntimeMode, RuntimeModeState, RuntimeStateStatus
from apps.safety_guard.models import SafetyPolicyConfig, SafetyStatus
from apps.go_live_gate.models import GoLiveChecklistRun, GoLiveGateStateCode


def _latest_certification() -> CertificationRun | None:
    return CertificationRun.objects.select_related('operating_envelope').order_by('-created_at', '-id').first()


def run_checklist(
    requested_by: str = 'local-operator',
    context: str = 'manual',
    metadata: dict | None = None,
    manual_inputs: dict | None = None,
) -> GoLiveChecklistRun:
    manual_inputs = manual_inputs or {}
    metadata = metadata or {}

    passed_items: list[str] = []
    failed_items: list[str] = []
    blocking_reasons: list[str] = []

    cert = _latest_certification()
    if cert and cert.certification_level in {
        CertificationLevel.PAPER_CERTIFIED_DEFENSIVE,
        CertificationLevel.PAPER_CERTIFIED_BALANCED,
        CertificationLevel.PAPER_CERTIFIED_HIGH_AUTONOMY,
    }:
        passed_items.append('certification_sufficient_for_prelive')
    else:
        failed_items.append('certification_sufficient_for_prelive')
        blocking_reasons.append('Certification is missing or below paper-certified level.')

    if cert and cert.certification_level == CertificationLevel.REMEDIATION_REQUIRED:
        failed_items.append('certification_not_in_remediation')
        blocking_reasons.append('Certification board requires remediation before pre-live rehearsal.')
    else:
        passed_items.append('certification_not_in_remediation')

    if cert and cert.operating_envelope and cert.operating_envelope.max_autonomy_mode_allowed in {RuntimeMode.PAPER_ASSIST, RuntimeMode.PAPER_SEMI_AUTO, RuntimeMode.PAPER_AUTO}:
        passed_items.append('operating_envelope_supports_prelive')
    else:
        failed_items.append('operating_envelope_supports_prelive')
        blocking_reasons.append('Operating envelope does not expose a supported paper runtime mode for rehearsal.')

    critical_open_incidents = IncidentRecord.objects.filter(severity=IncidentSeverity.CRITICAL).exclude(status=IncidentStatus.RESOLVED).count()
    if critical_open_incidents == 0:
        passed_items.append('no_open_critical_incidents')
    else:
        failed_items.append('no_open_critical_incidents')
        blocking_reasons.append(f'{critical_open_incidents} critical incidents remain open.')

    runtime_state = RuntimeModeState.objects.order_by('-updated_at', '-id').first()
    if runtime_state and runtime_state.current_mode in {RuntimeMode.PAPER_ASSIST, RuntimeMode.PAPER_SEMI_AUTO, RuntimeMode.PAPER_AUTO} and runtime_state.status in {RuntimeStateStatus.ACTIVE, RuntimeStateStatus.DEGRADED}:
        passed_items.append('runtime_alignment')
    else:
        failed_items.append('runtime_alignment')
        blocking_reasons.append('Runtime state is not in a paper operational mode suitable for rehearsal.')

    safety = SafetyPolicyConfig.objects.order_by('-updated_at', '-id').first()
    if safety and safety.status not in {SafetyStatus.KILL_SWITCH, SafetyStatus.HARD_STOP} and not safety.kill_switch_enabled:
        passed_items.append('safety_alignment')
    else:
        failed_items.append('safety_alignment')
        blocking_reasons.append('Safety guard is hard stopped or kill switch enabled.')

    benchmark = ResilienceBenchmark.objects.order_by('-created_at', '-id').first()
    benchmark_threshold = Decimal(str(manual_inputs.get('chaos_score_threshold', '70')))
    if benchmark and benchmark.resilience_score >= benchmark_threshold:
        passed_items.append('chaos_benchmark_threshold')
    else:
        failed_items.append('chaos_benchmark_threshold')
        blocking_reasons.append('Chaos resilience benchmark is missing or below threshold.')

    dry_run_total = BrokerDryRun.objects.count()
    dry_run_accepted = BrokerDryRun.objects.filter(simulated_response=BrokerDryRunResponse.ACCEPTED).count()
    dry_run_success_rate = (dry_run_accepted / dry_run_total) if dry_run_total else 0.0
    min_success_rate = float(manual_inputs.get('dry_run_success_rate_min', 0.6))
    if dry_run_total > 0 and dry_run_success_rate >= min_success_rate:
        passed_items.append('dry_run_success_rate')
    else:
        failed_items.append('dry_run_success_rate')
        blocking_reasons.append('Dry-run bridge success rate is below configured threshold.')

    if bool(manual_inputs.get('operator_review_complete', False)):
        passed_items.append('operator_review_complete')
    else:
        failed_items.append('operator_review_complete')
        blocking_reasons.append('Operator review is required before final rehearsal.')

    gate_state = GoLiveGateStateCode.PRELIVE_REHEARSAL_READY if not failed_items else GoLiveGateStateCode.REMEDIATION_REQUIRED
    run = GoLiveChecklistRun.objects.create(
        requested_by=requested_by,
        context=context,
        checklist_version='v1',
        passed=not failed_items,
        gate_state=gate_state,
        passed_items=passed_items,
        failed_items=failed_items,
        blocking_reasons=blocking_reasons,
        evidence={
            'certification_id': cert.id if cert else None,
            'critical_open_incidents': critical_open_incidents,
            'runtime_mode': runtime_state.current_mode if runtime_state else None,
            'runtime_status': runtime_state.status if runtime_state else None,
            'safety_status': safety.status if safety else None,
            'safety_kill_switch_enabled': safety.kill_switch_enabled if safety else None,
            'dry_run_total': dry_run_total,
            'dry_run_accepted': dry_run_accepted,
            'dry_run_success_rate': dry_run_success_rate,
            'latest_chaos_resilience_score': float(benchmark.resilience_score) if benchmark else None,
        },
        metadata=metadata,
    )
    return run
