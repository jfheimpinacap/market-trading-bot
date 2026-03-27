from __future__ import annotations

from apps.rollout_manager.models import RolloutDecision, RolloutDecisionCode, StackRolloutRun


def evaluate_rollout_decision(*, run: StackRolloutRun, metrics: dict | None = None) -> RolloutDecision:
    metrics = metrics or {}
    guardrails = run.plan.guardrails or {}
    min_sample = int(guardrails.get('min_sample_size', 20))
    completion_sample = int(guardrails.get('completion_sample_size', 100))
    recent_events = list(run.guardrail_events.order_by('-created_at')[:20])
    critical_events = [event for event in recent_events if event.severity == 'CRITICAL']

    decision = RolloutDecisionCode.CONTINUE_ROLLOUT
    reason_codes: list[str] = []
    rationale = 'Canary rollout remains within conservative guardrails.'

    if critical_events:
        decision = RolloutDecisionCode.ROLLBACK_NOW
        reason_codes = [event.code for event in critical_events]
        rationale = 'Critical guardrails triggered; immediate rollback is recommended.'
    elif run.routed_opportunities_count < min_sample:
        decision = RolloutDecisionCode.EXTEND_CANARY
        reason_codes = ['INSUFFICIENT_SAMPLE']
        rationale = 'Insufficient canary sample for a reliable promotion decision.'
    elif metrics.get('execution_adjusted_pnl_delta', 0) < 0 or metrics.get('fill_rate_delta', 0) < 0:
        decision = RolloutDecisionCode.PAUSE_ROLLOUT
        reason_codes = ['PERFORMANCE_SOFTENING']
        rationale = 'Performance softened during canary; pause and inspect before continuing.'
    elif run.routed_opportunities_count >= completion_sample and run.canary_count > 0:
        decision = RolloutDecisionCode.COMPLETE_PROMOTION
        reason_codes = ['STABLE_CANARY_SAMPLE']
        rationale = 'Canary sample sustained performance and reached completion threshold.'

    return RolloutDecision.objects.create(
        run=run,
        decision=decision,
        rationale=rationale,
        reason_codes=reason_codes,
        recommendation_payload={
            'routed_opportunities_count': run.routed_opportunities_count,
            'canary_count': run.canary_count,
            'champion_count': run.champion_count,
            'recent_guardrails': [event.code for event in recent_events[:5]],
            'input_metrics': metrics,
        },
    )
