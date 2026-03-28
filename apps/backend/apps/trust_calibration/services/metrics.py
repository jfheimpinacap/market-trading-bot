from decimal import Decimal


def safe_rate(numerator: int, denominator: int) -> Decimal:
    if denominator <= 0:
        return Decimal('0')
    return (Decimal(numerator) / Decimal(denominator)).quantize(Decimal('0.0001'))


def build_snapshot_metrics(*, granted: int, rejected: int, expired: int, escalated: int, auto_executed: int, auto_failed: int, blocked: int, retries: int, overrides: int, incidents: int) -> dict:
    total_approvals = granted + rejected + expired + escalated
    total_human = granted + rejected
    auto_success = max(auto_executed - auto_failed, 0)
    blocked_then_approved = min(blocked, granted)

    metrics = {
        'sample_size': total_approvals + auto_executed,
        'approval_rate': safe_rate(granted, total_approvals),
        'rejection_rate': safe_rate(rejected, total_approvals),
        'expiry_rate': safe_rate(expired, total_approvals),
        'escalation_rate': safe_rate(escalated, total_approvals),
        'auto_execution_success_rate': safe_rate(auto_success, auto_executed),
        'auto_execution_reversal_rate': safe_rate(auto_failed, auto_executed),
        'approval_friction_score': safe_rate(rejected + expired + escalated + blocked + retries, max(total_approvals + blocked, 1)),
        'operator_override_rate': safe_rate(overrides, max(auto_executed, 1)),
        'manual_intervention_rate': safe_rate(total_human + blocked + retries, max(total_approvals + auto_executed, 1)),
        'blocked_but_approved_later_ratio': safe_rate(blocked_then_approved, max(blocked, 1)),
        'auto_action_followed_by_incident_rate': safe_rate(incidents, max(auto_executed, 1)),
    }
    return {key: (str(value) if isinstance(value, Decimal) else value) for key, value in metrics.items()}
