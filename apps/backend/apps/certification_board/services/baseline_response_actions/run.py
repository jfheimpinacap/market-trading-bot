from __future__ import annotations

from collections import Counter

from django.db import transaction
from django.utils import timezone

from apps.certification_board.models import (
    BaselineResponseActionRun,
    BaselineResponseCase,
    BaselineResponseRun,
    ResponseActionRecommendation,
    ResponseActionRecommendationType,
    ResponseRoutingAction,
    ResponseRoutingActionStatus,
)
from apps.certification_board.services.baseline_response_actions.action_planning import plan_routing_actions
from apps.certification_board.services.baseline_response_actions.candidate_building import build_action_candidates
from apps.certification_board.services.baseline_response_actions.recommendation import build_action_recommendation


@transaction.atomic
def run_baseline_response_actions(*, actor: str = 'operator-ui', metadata: dict | None = None) -> dict:
    started_at = timezone.now()
    linked_response_run = BaselineResponseRun.objects.order_by('-started_at', '-id').first()
    action_run = BaselineResponseActionRun.objects.create(
        started_at=started_at,
        linked_baseline_response_run=linked_response_run,
        metadata={'actor': actor, 'manual_first': True, 'paper_only': True, **(metadata or {})},
    )

    candidates = build_action_candidates(action_run=action_run)
    actions = plan_routing_actions(candidates=candidates)
    recommendations = [build_action_recommendation(action_run=action_run, action=action) for action in actions]

    action_run.completed_at = timezone.now()
    action_run.candidate_count = len(candidates)
    action_run.ready_to_route_count = sum(1 for action in actions if action.action_status == ResponseRoutingActionStatus.READY_TO_ROUTE)
    action_run.routed_count = ResponseRoutingAction.objects.filter(action_status=ResponseRoutingActionStatus.ROUTED).count()
    action_run.blocked_count = sum(1 for action in actions if action.action_status == ResponseRoutingActionStatus.BLOCKED)
    action_run.under_review_count = BaselineResponseCase.objects.filter(case_status='UNDER_REVIEW').count()
    action_run.closed_count = BaselineResponseCase.objects.filter(case_status='CLOSED_NO_ACTION').count()
    action_run.recommendation_summary = dict(Counter(item.recommendation_type for item in recommendations))
    action_run.save(
        update_fields=[
            'completed_at',
            'candidate_count',
            'ready_to_route_count',
            'routed_count',
            'blocked_count',
            'under_review_count',
            'closed_count',
            'recommendation_summary',
            'updated_at',
        ]
    )

    return {
        'run': action_run,
        'candidates': candidates,
        'actions': actions,
        'recommendations': recommendations,
    }


def build_baseline_response_action_summary() -> dict:
    latest_run = BaselineResponseActionRun.objects.order_by('-started_at', '-id').first()
    return {
        'latest_run': latest_run,
        'response_cases_reviewed': latest_run.candidate_count if latest_run else 0,
        'ready_to_route': latest_run.ready_to_route_count if latest_run else 0,
        'routed': latest_run.routed_count if latest_run else 0,
        'blocked': latest_run.blocked_count if latest_run else 0,
        'under_review': latest_run.under_review_count if latest_run else 0,
        'closed': latest_run.closed_count if latest_run else 0,
        'recommendation_summary': latest_run.recommendation_summary if latest_run else {},
        'action_status_summary': dict(Counter(ResponseRoutingAction.objects.values_list('action_status', flat=True))),
        'recommendation_type_summary': dict(
            Counter(ResponseActionRecommendation.objects.values_list('recommendation_type', flat=True))
        ),
    }
