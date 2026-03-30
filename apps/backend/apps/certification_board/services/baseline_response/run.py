from __future__ import annotations

from collections import Counter

from django.db import transaction
from django.utils import timezone

from apps.certification_board.models import (
    BaselineHealthRun,
    BaselineResponseCase,
    BaselineResponseRecommendation,
    BaselineResponseRun,
    BaselineResponseType,
    ResponseEvidencePack,
    ResponseRoutingDecision,
)
from apps.certification_board.services.baseline_response.candidate_building import build_response_cases
from apps.certification_board.services.baseline_response.evidence_pack import build_response_evidence_pack
from apps.certification_board.services.baseline_response.recommendation import build_response_recommendation
from apps.certification_board.services.baseline_response.routing import build_routing_decision


@transaction.atomic
def run_baseline_response_review(*, actor: str = 'operator-ui', metadata: dict | None = None) -> dict:
    started_at = timezone.now()
    linked_health_run = BaselineHealthRun.objects.order_by('-started_at', '-id').first()
    run = BaselineResponseRun.objects.create(
        started_at=started_at,
        linked_baseline_health_run=linked_health_run,
        metadata={'actor': actor, 'manual_first': True, 'paper_only': True, **(metadata or {})},
    )

    cases = build_response_cases(review_run=run)
    evidence_packs = [build_response_evidence_pack(response_case=item) for item in cases]
    routing_decisions = [build_routing_decision(response_case=item) for item in cases]
    recommendations = [
        build_response_recommendation(review_run=run, response_case=item, evidence_pack=evidence)
        for item, evidence in zip(cases, evidence_packs)
    ]

    run.completed_at = timezone.now()
    run.candidate_count = len(cases)
    run.opened_case_count = BaselineResponseCase.objects.filter(review_run=run, case_status='OPEN').count()
    run.watch_case_count = BaselineResponseCase.objects.filter(review_run=run, response_type=BaselineResponseType.KEEP_UNDER_WATCH).count()
    run.reevaluation_case_count = BaselineResponseCase.objects.filter(review_run=run, response_type=BaselineResponseType.OPEN_REEVALUATION).count()
    run.tuning_case_count = BaselineResponseCase.objects.filter(review_run=run, response_type=BaselineResponseType.OPEN_TUNING_REVIEW).count()
    run.rollback_review_case_count = BaselineResponseCase.objects.filter(
        review_run=run,
        response_type=BaselineResponseType.PREPARE_ROLLBACK_REVIEW,
    ).count()
    run.recommendation_summary = dict(Counter(item.recommendation_type for item in recommendations))
    run.save(
        update_fields=[
            'completed_at',
            'candidate_count',
            'opened_case_count',
            'watch_case_count',
            'reevaluation_case_count',
            'tuning_case_count',
            'rollback_review_case_count',
            'recommendation_summary',
            'updated_at',
        ]
    )

    return {
        'run': run,
        'cases': cases,
        'evidence_packs': evidence_packs,
        'routing_decisions': routing_decisions,
        'recommendations': recommendations,
    }


def build_baseline_response_summary() -> dict:
    latest_run = BaselineResponseRun.objects.order_by('-started_at', '-id').first()
    return {
        'latest_run': latest_run,
        'active_baselines_reviewed': latest_run.candidate_count if latest_run else 0,
        'open_response_cases': latest_run.opened_case_count if latest_run else 0,
        'reevaluation_case_count': latest_run.reevaluation_case_count if latest_run else 0,
        'tuning_case_count': latest_run.tuning_case_count if latest_run else 0,
        'rollback_review_case_count': latest_run.rollback_review_case_count if latest_run else 0,
        'watch_case_count': latest_run.watch_case_count if latest_run else 0,
        'recommendation_summary': latest_run.recommendation_summary if latest_run else {},
        'case_status_summary': dict(Counter(BaselineResponseCase.objects.values_list('case_status', flat=True))),
        'routing_status_summary': dict(Counter(ResponseRoutingDecision.objects.values_list('routing_status', flat=True))),
        'evidence_status_summary': dict(Counter(ResponseEvidencePack.objects.values_list('evidence_status', flat=True))),
        'recommendation_type_summary': dict(
            Counter(BaselineResponseRecommendation.objects.values_list('recommendation_type', flat=True))
        ),
    }
