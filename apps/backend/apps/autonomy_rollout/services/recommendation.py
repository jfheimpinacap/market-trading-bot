from __future__ import annotations

from decimal import Decimal

from apps.autonomy_rollout.models import (
    AutonomyRolloutRecommendation,
    AutonomyRolloutRecommendationCode,
    AutonomyRolloutRun,
    AutonomyRolloutStatus,
)


def _d(value: object) -> Decimal:
    return Decimal(str(value or '0'))


def evaluate_rollout(run: AutonomyRolloutRun) -> AutonomyRolloutRecommendation:
    post = run.post_change_snapshot
    deltas = post.deltas
    sample_size = post.sample_size

    reason_codes: list[str] = []
    warnings: list[str] = []
    cross_domain_notes: list[dict] = []

    incident_delta = _d(deltas.get('incident_after_auto_rate'))
    friction_delta = _d(deltas.get('approval_friction_score'))
    blocked_delta = _d(deltas.get('blocked_rate'))
    degraded_delta = _d(deltas.get('degraded_context_rate'))
    auto_success_delta = _d(deltas.get('auto_execution_success_rate'))

    cross_domain_incidents = int(post.counts.get('cross_domain_incidents') or 0)
    if cross_domain_incidents > 0:
        cross_domain_notes.append({
            'domain_impacted': 'multi',
            'suspected_source_domain': run.domain.slug,
            'related_signals': {'cross_domain_incidents': cross_domain_incidents},
            'cross_domain_warning': True,
        })

    recommendation = AutonomyRolloutRecommendationCode.REQUIRE_MORE_DATA
    rollout_status = AutonomyRolloutStatus.OBSERVING
    rationale = 'Need a larger post-change sample before deciding if the domain stage should be kept or reverted.'

    if sample_size < 5:
        reason_codes.append('LOW_SAMPLE_SIZE')
    elif incident_delta >= Decimal('0.1000') or auto_success_delta <= Decimal('-0.1500'):
        recommendation = AutonomyRolloutRecommendationCode.ROLLBACK_STAGE
        rollout_status = AutonomyRolloutStatus.ROLLBACK_RECOMMENDED
        rationale = 'Post-change safety degraded materially for this domain; manual rollback is recommended.'
        reason_codes.extend(['INCIDENT_RATE_WORSE', 'AUTO_SUCCESS_DEGRADED'])
        warnings.append('Rollback is manual-first and requires explicit operator confirmation.')
    elif blocked_delta >= Decimal('0.1500') or degraded_delta >= Decimal('0.1000'):
        recommendation = AutonomyRolloutRecommendationCode.FREEZE_DOMAIN
        rollout_status = AutonomyRolloutStatus.FREEZE_RECOMMENDED
        rationale = 'Post-change friction/degraded posture increased; freeze is recommended pending stabilization.'
        reason_codes.extend(['BLOCKED_RATE_INCREASED', 'DEGRADED_CONTEXT_INCREASED'])
        warnings.append('Freeze should be approval-gated for high-impact domains.')
    elif friction_delta >= Decimal('0.1000'):
        recommendation = AutonomyRolloutRecommendationCode.STABILIZE_AND_MONITOR
        rollout_status = AutonomyRolloutStatus.CAUTION
        rationale = 'Friction increased without hard rollback trigger; continue manual-first stabilization and monitoring.'
        reason_codes.append('FRICTION_INCREASED')
    elif incident_delta <= Decimal('0.0000') and friction_delta <= Decimal('0.0000') and auto_success_delta >= Decimal('0.0500'):
        recommendation = AutonomyRolloutRecommendationCode.KEEP_STAGE
        rollout_status = AutonomyRolloutStatus.STABLE
        rationale = 'Post-change metrics show stable/improved safety and execution signal for this domain stage.'
        reason_codes.extend(['SAFETY_STABLE', 'AUTO_SUCCESS_IMPROVED'])
    else:
        recommendation = AutonomyRolloutRecommendationCode.REVIEW_MANUALLY
        rollout_status = AutonomyRolloutStatus.CAUTION
        rationale = 'Signals are mixed; review traces/incidents and approval flow before deciding.'
        reason_codes.append('MIXED_SIGNAL')

    rec = AutonomyRolloutRecommendation.objects.create(
        run=run,
        recommendation=recommendation,
        rationale=rationale,
        reason_codes=reason_codes,
        confidence=post.confidence,
        supporting_deltas=deltas,
        warnings=warnings,
        cross_domain_notes=cross_domain_notes,
        metadata={
            'sample_size': sample_size,
            'manual_first': True,
            'paper_only': True,
        },
    )

    run.rollout_status = rollout_status
    run.summary = rationale
    if recommendation == AutonomyRolloutRecommendationCode.KEEP_STAGE:
        run.rollout_status = AutonomyRolloutStatus.COMPLETED
    run.save(update_fields=['rollout_status', 'summary', 'updated_at'])
    return rec
