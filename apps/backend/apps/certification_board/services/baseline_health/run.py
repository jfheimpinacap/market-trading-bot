from __future__ import annotations

from collections import Counter

from django.db import transaction
from django.utils import timezone

from apps.certification_board.models import (
    BaselineActivationRun,
    BaselineHealthCandidate,
    BaselineHealthRecommendation,
    BaselineHealthRun,
    BaselineHealthSignal,
    BaselineHealthStatus,
    BaselineHealthStatusCode,
)
from apps.certification_board.services.baseline_health.candidate_building import build_baseline_health_candidates
from apps.certification_board.services.baseline_health.health_status import derive_health_status
from apps.certification_board.services.baseline_health.recommendation import build_baseline_health_recommendation
from apps.certification_board.services.baseline_health.signals import gather_recent_signals


@transaction.atomic
def run_baseline_health_review(*, actor: str = 'operator-ui', metadata: dict | None = None) -> dict:
    started_at = timezone.now()
    linked_activation_run = BaselineActivationRun.objects.order_by('-started_at', '-id').first()
    run = BaselineHealthRun.objects.create(
        started_at=started_at,
        linked_baseline_activation_run=linked_activation_run,
        metadata={'actor': actor, **(metadata or {})},
    )

    candidates = build_baseline_health_candidates(review_run=run)
    statuses: list[BaselineHealthStatus] = []
    signals: list[BaselineHealthSignal] = []
    recommendations: list[BaselineHealthRecommendation] = []

    for candidate in candidates:
        consolidated = gather_recent_signals(
            target_component=candidate.target_component,
            target_scope=candidate.target_scope,
        )
        result = derive_health_status(candidate=candidate, consolidated=consolidated)

        status = BaselineHealthStatus.objects.create(
            linked_candidate=candidate,
            health_status=result['health_status'],
            calibration_health_score=result['calibration_health_score'],
            risk_gate_health_score=result['risk_gate_health_score'],
            opportunity_quality_health_score=result['opportunity_quality_health_score'],
            drift_risk_score=result['drift_risk_score'],
            regression_risk_score=result['regression_risk_score'],
            rationale=result['rationale'],
            reason_codes=result['reason_codes'],
            blockers=result['blockers'],
            metadata=result['metadata'],
        )
        statuses.append(status)

        for payload in result['signals']:
            signals.append(
                BaselineHealthSignal.objects.create(
                    linked_status=status,
                    signal_type=payload['signal_type'],
                    signal_severity=payload['signal_severity'],
                    signal_direction=payload['signal_direction'],
                    evidence_summary=payload['evidence_summary'],
                    rationale=payload['rationale'],
                    metadata={'candidate_id': candidate.id},
                )
            )

        recommendations.append(build_baseline_health_recommendation(review_run=run, status=status))

    run.completed_at = timezone.now()
    run.active_binding_count = BaselineHealthCandidate.objects.filter(review_run=run).count()
    run.healthy_count = BaselineHealthStatus.objects.filter(
        linked_candidate__review_run=run, health_status=BaselineHealthStatusCode.HEALTHY
    ).count()
    run.watch_count = BaselineHealthStatus.objects.filter(
        linked_candidate__review_run=run,
        health_status__in=[BaselineHealthStatusCode.UNDER_WATCH, BaselineHealthStatusCode.INSUFFICIENT_DATA],
    ).count()
    run.degraded_count = BaselineHealthStatus.objects.filter(
        linked_candidate__review_run=run, health_status=BaselineHealthStatusCode.DEGRADED
    ).count()
    run.review_required_count = BaselineHealthStatus.objects.filter(
        linked_candidate__review_run=run, health_status=BaselineHealthStatusCode.REVIEW_REQUIRED
    ).count()
    run.rollback_review_count = BaselineHealthStatus.objects.filter(
        linked_candidate__review_run=run, health_status=BaselineHealthStatusCode.ROLLBACK_REVIEW_RECOMMENDED
    ).count()
    run.recommendation_summary = dict(Counter(item.recommendation_type for item in recommendations))
    run.save(
        update_fields=[
            'completed_at',
            'active_binding_count',
            'healthy_count',
            'watch_count',
            'degraded_count',
            'review_required_count',
            'rollback_review_count',
            'recommendation_summary',
            'updated_at',
        ]
    )

    return {
        'run': run,
        'candidates': candidates,
        'statuses': statuses,
        'signals': signals,
        'recommendations': recommendations,
    }
