from __future__ import annotations

from django.db import models
from django.utils import timezone

from apps.portfolio_governor.models import (
    PortfolioExposureApplyDecision,
    PortfolioExposureApplyRecommendation,
    PortfolioExposureApplyRecord,
    PortfolioExposureApplyRun,
    PortfolioExposureDecision,
    PortfolioExposureConflictReview,
    PortfolioExposureCoordinationRun,
    PortfolioExposureRecommendation,
)
from apps.portfolio_governor.services.apply_decision import derive_apply_decision
from apps.portfolio_governor.services.apply_record import execute_apply_decision
from apps.portfolio_governor.services.apply_targets import resolve_apply_targets
from apps.portfolio_governor.services.clusters import build_cluster_snapshots
from apps.portfolio_governor.services.conflict_review import review_cluster_conflicts
from apps.portfolio_governor.services.decision import derive_exposure_decision
from apps.portfolio_governor.services.governance import get_latest_throttle_decision
from apps.portfolio_governor.services.recommendation import create_apply_recommendation, create_exposure_recommendation


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


def apply_exposure_decision(*, decision: PortfolioExposureDecision, force_apply: bool = False, triggered_by: str = 'manual_api') -> PortfolioExposureApplyRun:
    apply_run = PortfolioExposureApplyRun.objects.create(
        started_at=timezone.now(),
        metadata={'triggered_by': triggered_by, 'single_decision_id': decision.id, 'paper_only': True},
    )
    _process_decisions(apply_run=apply_run, decisions=[decision], force_apply=force_apply)
    _finalize_apply_run(apply_run)
    return apply_run


def run_exposure_apply_review(*, force_apply: bool = False, triggered_by: str = 'manual_api') -> PortfolioExposureApplyRun:
    decisions = list(
        PortfolioExposureDecision.objects.select_related('linked_cluster_snapshot')
        .filter(decision_status='PROPOSED')
        .order_by('-created_at_decision', '-id')[:50]
    )
    apply_run = PortfolioExposureApplyRun.objects.create(
        started_at=timezone.now(),
        metadata={'triggered_by': triggered_by, 'paper_only': True, 'decision_batch': len(decisions)},
    )
    _process_decisions(apply_run=apply_run, decisions=decisions, force_apply=force_apply)
    _finalize_apply_run(apply_run)
    return apply_run


def _process_decisions(*, apply_run: PortfolioExposureApplyRun, decisions: list[PortfolioExposureDecision], force_apply: bool):
    for decision in decisions:
        target_resolution = resolve_apply_targets(apply_run=apply_run, decision=decision)
        apply_decision = derive_apply_decision(
            apply_run=apply_run,
            decision=decision,
            targets=target_resolution.targets,
            resolver_reason_codes=target_resolution.reason_codes,
        )
        create_apply_recommendation(exposure_decision=decision, apply_decision=apply_decision)
        execute_apply_decision(apply_decision=apply_decision, force_apply=force_apply)


def _finalize_apply_run(apply_run: PortfolioExposureApplyRun):
    decisions = PortfolioExposureApplyDecision.objects.filter(linked_apply_run=apply_run)
    records = PortfolioExposureApplyRecord.objects.filter(linked_apply_decision__linked_apply_run=apply_run)

    apply_run.considered_decision_count = decisions.count()
    apply_run.applied_count = decisions.filter(apply_status='APPLIED').count()
    apply_run.skipped_count = decisions.filter(apply_status='SKIPPED').count()
    apply_run.blocked_count = decisions.filter(apply_status='BLOCKED').count()
    apply_run.deferred_dispatch_apply_count = records.filter(effect_type='DISPATCH_DEFERRED', record_status='APPLIED').count()
    apply_run.parked_session_apply_count = records.filter(effect_type='SESSION_PARKED', record_status='APPLIED').count()
    apply_run.paused_cluster_apply_count = records.filter(effect_type='CLUSTER_ACTIVITY_PAUSED', record_status='APPLIED').count()
    apply_run.recommendation_summary = {
        item['recommendation_type']: item['count']
        for item in PortfolioExposureApplyRecommendation.objects.filter(target_apply_decision__linked_apply_run=apply_run)
        .values('recommendation_type')
        .annotate(count=models.Count('id'))
        .order_by('recommendation_type')
    }
    apply_run.completed_at = timezone.now()
    apply_run.save(
        update_fields=[
            'considered_decision_count',
            'applied_count',
            'skipped_count',
            'blocked_count',
            'deferred_dispatch_apply_count',
            'parked_session_apply_count',
            'paused_cluster_apply_count',
            'recommendation_summary',
            'completed_at',
            'updated_at',
        ]
    )


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


def build_exposure_apply_summary() -> dict:
    latest_run = PortfolioExposureApplyRun.objects.order_by('-started_at', '-id').first()
    if latest_run is None:
        return {
            'latest_run_id': None,
            'decisions_considered': 0,
            'applied': 0,
            'skipped': 0,
            'blocked': 0,
            'deferred_dispatches': 0,
            'parked_sessions': 0,
            'paused_clusters': 0,
            'paper_demo_only': True,
            'real_execution_enabled': False,
        }
    return {
        'latest_run_id': latest_run.id,
        'decisions_considered': latest_run.considered_decision_count,
        'applied': latest_run.applied_count,
        'skipped': latest_run.skipped_count,
        'blocked': latest_run.blocked_count,
        'deferred_dispatches': latest_run.deferred_dispatch_apply_count,
        'parked_sessions': latest_run.parked_session_apply_count,
        'paused_clusters': latest_run.paused_cluster_apply_count,
        'recommendation_summary': latest_run.recommendation_summary,
        'paper_demo_only': True,
        'real_execution_enabled': False,
    }
