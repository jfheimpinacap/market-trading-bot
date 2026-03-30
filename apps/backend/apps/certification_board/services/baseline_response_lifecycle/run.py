from __future__ import annotations

from collections import Counter

from django.db import transaction
from django.utils import timezone

from apps.certification_board.models import (
    BaselineResponseActionRun,
    BaselineResponseLifecycleRun,
    DownstreamAcknowledgement,
    DownstreamAcknowledgementStatus,
    DownstreamLifecycleOutcome,
    DownstreamLifecycleOutcomeType,
    ResponseLifecycleRecommendation,
    ResponseRoutingAction,
    ResponseRoutingActionStatus,
)
from apps.certification_board.services.baseline_response_lifecycle.outcomes import record_or_update_outcome
from apps.certification_board.services.baseline_response_lifecycle.recommendation import build_lifecycle_recommendation
from apps.certification_board.services.baseline_response_lifecycle.stages import latest_stage_for_case


@transaction.atomic
def run_baseline_response_lifecycle(*, actor: str = 'operator-ui', metadata: dict | None = None) -> dict:
    run = BaselineResponseLifecycleRun.objects.create(
        started_at=timezone.now(),
        linked_baseline_response_action_run=BaselineResponseActionRun.objects.order_by('-started_at', '-id').first(),
        metadata={'actor': actor, 'manual_first': True, 'paper_only': True, **(metadata or {})},
    )
    routed_actions = list(
        ResponseRoutingAction.objects.filter(action_status=ResponseRoutingActionStatus.ROUTED)
        .select_related('linked_response_case')
        .order_by('-created_at', '-id')[:500]
    )

    recommendations = []
    outcomes = []
    for action in routed_actions:
        response_case = action.linked_response_case
        acknowledgement = DownstreamAcknowledgement.objects.filter(linked_response_case=response_case).order_by('-created_at', '-id').first()
        if acknowledgement is None:
            acknowledgement = DownstreamAcknowledgement.objects.create(
                linked_response_routing_action=action,
                linked_response_case=response_case,
                routing_target=action.routing_target,
                acknowledgement_status=DownstreamAcknowledgementStatus.SENT,
                acknowledgement_notes='Case routed; waiting downstream acknowledgement update.',
                metadata={'source': 'lifecycle-run-default'},
            )

        stage = latest_stage_for_case(response_case)
        outcome = record_or_update_outcome(
            response_case=response_case,
            acknowledgement=acknowledgement,
            latest_stage=stage,
            linked_target_reference=acknowledgement.linked_target_reference,
            metadata={'source': 'baseline-response-lifecycle-run'},
        )
        outcomes.append(outcome)
        recommendations.append(build_lifecycle_recommendation(lifecycle_run=run, response_case=response_case, acknowledgement=acknowledgement, outcome=outcome))

    acknowledgement_statuses = Counter(DownstreamAcknowledgement.objects.values_list('acknowledgement_status', flat=True))
    outcome_types = Counter(DownstreamLifecycleOutcome.objects.values_list('outcome_type', flat=True))

    run.completed_at = timezone.now()
    run.routed_action_count = len(routed_actions)
    run.acknowledged_count = acknowledgement_statuses.get(DownstreamAcknowledgementStatus.ACKNOWLEDGED, 0)
    run.accepted_for_review_count = acknowledgement_statuses.get(DownstreamAcknowledgementStatus.ACCEPTED_FOR_REVIEW, 0)
    run.waiting_evidence_count = acknowledgement_statuses.get(DownstreamAcknowledgementStatus.WAITING_MORE_EVIDENCE, 0)
    run.resolved_downstream_count = outcome_types.get(DownstreamLifecycleOutcomeType.RESOLVED_BY_TARGET, 0)
    run.rejected_downstream_count = outcome_types.get(DownstreamLifecycleOutcomeType.REJECTED_BY_TARGET, 0)
    run.recommendation_summary = dict(Counter(item.recommendation_type for item in recommendations))
    run.save(update_fields=['completed_at', 'routed_action_count', 'acknowledged_count', 'accepted_for_review_count', 'waiting_evidence_count', 'resolved_downstream_count', 'rejected_downstream_count', 'recommendation_summary', 'updated_at'])

    return {'run': run, 'outcomes': outcomes, 'recommendations': recommendations}


def build_response_lifecycle_summary() -> dict:
    latest_run = BaselineResponseLifecycleRun.objects.order_by('-started_at', '-id').first()
    return {
        'latest_run': latest_run,
        'routed_cases': latest_run.routed_action_count if latest_run else 0,
        'acknowledged': latest_run.acknowledged_count if latest_run else 0,
        'accepted_for_review': latest_run.accepted_for_review_count if latest_run else 0,
        'waiting_evidence': latest_run.waiting_evidence_count if latest_run else 0,
        'resolved_downstream': latest_run.resolved_downstream_count if latest_run else 0,
        'rejected_downstream': latest_run.rejected_downstream_count if latest_run else 0,
        'recommendation_summary': latest_run.recommendation_summary if latest_run else {},
        'acknowledgement_status_summary': dict(Counter(DownstreamAcknowledgement.objects.values_list('acknowledgement_status', flat=True))),
        'outcome_type_summary': dict(Counter(DownstreamLifecycleOutcome.objects.values_list('outcome_type', flat=True))),
        'recommendation_type_summary': dict(Counter(ResponseLifecycleRecommendation.objects.values_list('recommendation_type', flat=True))),
    }
