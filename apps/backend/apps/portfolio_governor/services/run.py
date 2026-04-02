from __future__ import annotations

from django.db import models
from django.utils import timezone

from apps.portfolio_governor.models import (
    PortfolioExposureConflictReview,
    PortfolioExposureCoordinationRun,
    PortfolioExposureDecision,
    PortfolioExposureRecommendation,
)
from apps.portfolio_governor.services.clusters import build_cluster_snapshots
from apps.portfolio_governor.services.conflict_review import review_cluster_conflicts
from apps.portfolio_governor.services.decision import derive_exposure_decision
from apps.portfolio_governor.services.governance import get_latest_throttle_decision
from apps.portfolio_governor.services.recommendation import create_exposure_recommendation


def run_exposure_coordination_review(*, triggered_by: str = 'manual_api') -> PortfolioExposureCoordinationRun:
    latest_throttle = get_latest_throttle_decision()
    throttle_state = latest_throttle.state if latest_throttle else 'NORMAL'
    run = PortfolioExposureCoordinationRun.objects.create(
        started_at=timezone.now(),
        metadata={'triggered_by': triggered_by, 'paper_only': True, 'real_execution_enabled': False},
    )

    clusters = build_cluster_snapshots(run=run, portfolio_throttle_state=throttle_state)
    for cluster in clusters:
        reviews = review_cluster_conflicts(cluster=cluster)
        for review in reviews:
            decision = derive_exposure_decision(review=review)
            create_exposure_recommendation(decision=decision)

    decisions = PortfolioExposureDecision.objects.filter(linked_cluster_snapshot__linked_run=run)
    run.considered_cluster_count = len(clusters)
    run.concentration_alert_count = PortfolioExposureConflictReview.objects.filter(
        linked_cluster_snapshot__linked_run=run,
        review_type='CONCENTRATION_RISK',
    ).count()
    run.conflict_alert_count = PortfolioExposureConflictReview.objects.filter(
        linked_cluster_snapshot__linked_run=run,
        review_type__in=['DIRECTIONAL_CONFLICT', 'PORTFOLIO_PRESSURE_CONFLICT'],
    ).count()
    run.throttle_count = decisions.filter(decision_type='THROTTLE_NEW_ENTRIES').count()
    run.defer_count = decisions.filter(decision_type='DEFER_PENDING_DISPATCH').count()
    run.park_count = decisions.filter(decision_type='PARK_WEAKER_SESSION').count()
    run.manual_review_count = decisions.filter(decision_type='REQUIRE_MANUAL_EXPOSURE_REVIEW').count()
    run.recommendation_summary = {
        item['recommendation_type']: item['count']
        for item in PortfolioExposureRecommendation.objects.filter(target_exposure_decision__linked_cluster_snapshot__linked_run=run)
        .values('recommendation_type')
        .order_by('recommendation_type')
        .annotate(count=models.Count('id'))
    }
    run.completed_at = timezone.now()
    run.save(
        update_fields=[
            'considered_cluster_count',
            'concentration_alert_count',
            'conflict_alert_count',
            'throttle_count',
            'defer_count',
            'park_count',
            'manual_review_count',
            'recommendation_summary',
            'completed_at',
            'updated_at',
        ]
    )
    return run


def build_exposure_coordination_summary() -> dict:
    latest_run = PortfolioExposureCoordinationRun.objects.order_by('-started_at', '-id').first()
    if latest_run is None:
        return {
            'latest_run_id': None,
            'clusters_reviewed': 0,
            'concentration_alerts': 0,
            'conflict_alerts': 0,
            'throttles': 0,
            'defers': 0,
            'parks': 0,
            'manual_reviews': 0,
            'paper_demo_only': True,
            'real_execution_enabled': False,
        }

    return {
        'latest_run_id': latest_run.id,
        'clusters_reviewed': latest_run.considered_cluster_count,
        'concentration_alerts': latest_run.concentration_alert_count,
        'conflict_alerts': latest_run.conflict_alert_count,
        'throttles': latest_run.throttle_count,
        'defers': latest_run.defer_count,
        'parks': latest_run.park_count,
        'manual_reviews': latest_run.manual_review_count,
        'recommendation_summary': latest_run.recommendation_summary,
        'paper_demo_only': True,
        'real_execution_enabled': False,
    }
