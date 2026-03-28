from __future__ import annotations

from decimal import Decimal

from apps.policy_rollout.models import PolicyRolloutRecommendation, PolicyRolloutRecommendationCode, PolicyRolloutRun, PolicyRolloutStatus


def _d(value: object) -> Decimal:
    return Decimal(str(value or '0'))


def evaluate_rollout(run: PolicyRolloutRun) -> PolicyRolloutRecommendation:
    post = run.post_change_snapshot
    deltas = post.deltas
    sample_size = post.sample_size

    reason_codes: list[str] = []
    blockers: list[str] = []
    warnings: list[str] = []

    incident_delta = _d(deltas.get('auto_action_followed_by_incident_rate'))
    friction_delta = _d(deltas.get('approval_friction_score'))
    auto_success_delta = _d(deltas.get('auto_execution_success_rate'))
    blocked_delta = _d(deltas.get('manual_intervention_rate'))

    recommendation = PolicyRolloutRecommendationCode.REQUIRE_MORE_DATA
    rollout_status = PolicyRolloutStatus.OBSERVING
    rationale = 'Need a larger post-change sample before deciding whether to keep or rollback.'

    if sample_size < 5:
        reason_codes.append('LOW_SAMPLE_SIZE')
    elif incident_delta >= Decimal('0.1000') or auto_success_delta <= Decimal('-0.1500'):
        recommendation = PolicyRolloutRecommendationCode.ROLLBACK_CHANGE
        rollout_status = PolicyRolloutStatus.ROLLBACK_RECOMMENDED
        rationale = 'Post-change safety degraded materially; manual rollback is recommended.'
        reason_codes.extend(['INCIDENT_RATE_WORSE', 'AUTO_SUCCESS_DEGRADED'])
        blockers.append('Operator review + explicit rollback confirmation required.')
    elif friction_delta >= Decimal('0.1000') or blocked_delta >= Decimal('0.1500'):
        recommendation = PolicyRolloutRecommendationCode.STABILIZE_AND_MONITOR
        rollout_status = PolicyRolloutStatus.CAUTION
        rationale = 'No hard rollback trigger, but friction/intervention increased and requires closer monitoring.'
        reason_codes.extend(['FRICTION_INCREASED', 'MANUAL_INTERVENTION_INCREASED'])
        warnings.append('Keep manual-first approvals for sensitive actions until signal stabilizes.')
    elif incident_delta <= Decimal('0.0000') and friction_delta <= Decimal('0.0000') and auto_success_delta >= Decimal('0.0500'):
        recommendation = PolicyRolloutRecommendationCode.KEEP_CHANGE
        rollout_status = PolicyRolloutStatus.STABLE
        rationale = 'Post-change metrics show improved automation quality with stable safety signal.'
        reason_codes.extend(['SAFETY_STABLE', 'AUTO_SUCCESS_IMPROVED'])
    else:
        recommendation = PolicyRolloutRecommendationCode.REVIEW_MANUALLY
        rollout_status = PolicyRolloutStatus.CAUTION
        rationale = 'Signals are mixed; review traces/incidents manually before deciding final outcome.'
        reason_codes.append('MIXED_SIGNAL')

    rec = PolicyRolloutRecommendation.objects.create(
        run=run,
        recommendation=recommendation,
        rationale=rationale,
        reason_codes=reason_codes,
        confidence=post.confidence,
        supporting_deltas=deltas,
        blockers=blockers,
        warnings=warnings,
        metadata={
            'sample_size': sample_size,
            'manual_first': True,
            'paper_only': True,
        },
    )

    run.rollout_status = rollout_status
    run.summary = rationale
    if recommendation in {PolicyRolloutRecommendationCode.KEEP_CHANGE, PolicyRolloutRecommendationCode.ROLLBACK_CHANGE}:
        run.rollout_status = PolicyRolloutStatus.COMPLETED if recommendation == PolicyRolloutRecommendationCode.KEEP_CHANGE else PolicyRolloutStatus.ROLLBACK_RECOMMENDED
    run.save(update_fields=['rollout_status', 'summary', 'updated_at'])
    return rec
