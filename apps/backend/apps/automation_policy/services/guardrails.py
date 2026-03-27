from apps.certification_board.models import CertificationLevel, CertificationRun
from apps.incident_commander.models import DegradedModeState, DegradedSystemState
from apps.runtime_governor.models import RuntimeModeState, RuntimeStateStatus
from apps.safety_guard.models import SafetyPolicyConfig, SafetyStatus
from apps.automation_policy.models import AutomationTrustTier

TRUST_RANK = {
    AutomationTrustTier.AUTO_BLOCKED: 0,
    AutomationTrustTier.MANUAL_ONLY: 1,
    AutomationTrustTier.APPROVAL_REQUIRED: 2,
    AutomationTrustTier.SAFE_AUTOMATION: 3,
}


def _min_tier(left: str, right: str) -> str:
    return left if TRUST_RANK[left] <= TRUST_RANK[right] else right


def get_guardrail_snapshot() -> dict:
    runtime_state = RuntimeModeState.objects.order_by('-id').first()
    safety_config = SafetyPolicyConfig.objects.order_by('-id').first()
    cert = CertificationRun.objects.order_by('-created_at', '-id').first()
    degraded = DegradedModeState.objects.order_by('-updated_at', '-id').first()
    return {
        'runtime_state': runtime_state,
        'safety_config': safety_config,
        'certification_run': cert,
        'degraded_mode': degraded,
    }


def apply_guardrails(*, proposed_tier: str, action_type: str, recommendation_mode: bool) -> tuple[str, list[str], dict]:
    effective = proposed_tier
    reason_codes: list[str] = []
    snapshot = get_guardrail_snapshot()

    runtime_state = snapshot['runtime_state']
    if runtime_state and runtime_state.status in {RuntimeStateStatus.DEGRADED, RuntimeStateStatus.PAUSED, RuntimeStateStatus.STOPPED}:
        effective = _min_tier(effective, AutomationTrustTier.APPROVAL_REQUIRED)
        reason_codes.append('runtime_status_restricts_automation')

    safety_config = snapshot['safety_config']
    if safety_config and safety_config.status in {SafetyStatus.HARD_STOP, SafetyStatus.KILL_SWITCH, SafetyStatus.PAUSED}:
        effective = _min_tier(effective, AutomationTrustTier.MANUAL_ONLY)
        reason_codes.append('safety_status_requires_manual')

    cert = snapshot['certification_run']
    if cert and cert.certification_level in {CertificationLevel.REMEDIATION_REQUIRED, CertificationLevel.RECERTIFICATION_REQUIRED, CertificationLevel.NOT_CERTIFIED}:
        effective = _min_tier(effective, AutomationTrustTier.APPROVAL_REQUIRED)
        reason_codes.append('certification_downgrade')

    degraded = snapshot['degraded_mode']
    if degraded and degraded.state != DegradedSystemState.NORMAL:
        effective = _min_tier(effective, AutomationTrustTier.APPROVAL_REQUIRED)
        reason_codes.append('degraded_mode_active')

    if action_type in {'live_execution', 'broker_order_submit'}:
        effective = AutomationTrustTier.AUTO_BLOCKED
        reason_codes.append('live_execution_domain_blocked')

    if recommendation_mode and effective == AutomationTrustTier.SAFE_AUTOMATION:
        reason_codes.append('recommendation_mode_no_auto_execute')

    context = {
        'runtime': {
            'mode': runtime_state.current_mode if runtime_state else None,
            'status': runtime_state.status if runtime_state else None,
        },
        'safety': {
            'status': safety_config.status if safety_config else None,
            'kill_switch_enabled': bool(safety_config.kill_switch_enabled) if safety_config else False,
        },
        'certification': {
            'level': cert.certification_level if cert else None,
        },
        'degraded_mode': {
            'state': degraded.state if degraded else None,
            'disabled_actions': degraded.disabled_actions if degraded else [],
        },
    }
    return effective, sorted(set(reason_codes)), context
