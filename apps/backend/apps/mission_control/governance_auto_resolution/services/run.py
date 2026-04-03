from __future__ import annotations

from django.utils import timezone

from apps.mission_control.governance_auto_resolution.services.auto_resolve import apply_auto_resolution_decision
from apps.mission_control.governance_auto_resolution.services.eligibility import evaluate_auto_resolution_eligibility
from apps.mission_control.models import (
    GovernanceAutoResolutionDecision,
    GovernanceAutoResolutionDecisionStatus,
    GovernanceAutoResolutionDecisionType,
    GovernanceAutoResolutionRecord,
    GovernanceAutoResolutionRun,
    GovernanceReviewItem,
    GovernanceReviewItemStatus,
)


def run_governance_auto_resolution() -> GovernanceAutoResolutionRun:
    run = GovernanceAutoResolutionRun.objects.create(started_at=timezone.now())
    open_items = list(
        GovernanceReviewItem.objects.filter(
            item_status__in=[GovernanceReviewItemStatus.OPEN, GovernanceReviewItemStatus.IN_REVIEW],
        ).order_by('queue_priority', '-updated_at', '-id')[:300]
    )

    run.considered_item_count = len(open_items)

    for item in open_items:
        eligibility = evaluate_auto_resolution_eligibility(item)
        decision = GovernanceAutoResolutionDecision.objects.create(
            linked_review_item=item,
            linked_auto_resolution_run=run,
            decision_type=eligibility.decision_type,
            decision_status=GovernanceAutoResolutionDecisionStatus.PROPOSED,
            auto_applicable=eligibility.auto_applicable,
            decision_summary=eligibility.decision_summary,
            reason_codes=eligibility.reason_codes,
            metadata=eligibility.metadata,
        )

        if eligibility.auto_applicable and eligibility.decision_type != GovernanceAutoResolutionDecisionType.DO_NOT_AUTO_RESOLVE:
            run.eligible_count += 1

        record = apply_auto_resolution_decision(decision=decision)
        if record.record_status == 'APPLIED':
            run.applied_count += 1
        elif record.record_status == 'SKIPPED':
            run.skipped_count += 1
        else:
            run.blocked_count += 1

    run.completed_at = timezone.now()
    run.metadata = {
        'decision_count': GovernanceAutoResolutionDecision.objects.filter(linked_auto_resolution_run=run).count(),
        'record_count': GovernanceAutoResolutionRecord.objects.filter(linked_auto_resolution_decision__linked_auto_resolution_run=run).count(),
    }
    run.save()
    return run


def build_governance_auto_resolution_summary() -> dict:
    latest_run = GovernanceAutoResolutionRun.objects.order_by('-started_at', '-id').first()
    return {
        'latest_run_id': latest_run.id if latest_run else None,
        'totals': {
            'runs': GovernanceAutoResolutionRun.objects.count(),
            'decisions': GovernanceAutoResolutionDecision.objects.count(),
            'records': GovernanceAutoResolutionRecord.objects.count(),
        },
        'latest_counts': {
            'considered': latest_run.considered_item_count if latest_run else 0,
            'eligible': latest_run.eligible_count if latest_run else 0,
            'applied': latest_run.applied_count if latest_run else 0,
            'skipped': latest_run.skipped_count if latest_run else 0,
            'blocked': latest_run.blocked_count if latest_run else 0,
        },
        'decision_breakdown': {
            'auto_dismiss': GovernanceAutoResolutionDecision.objects.filter(decision_type=GovernanceAutoResolutionDecisionType.AUTO_DISMISS).count(),
            'auto_retry_safe_apply': GovernanceAutoResolutionDecision.objects.filter(decision_type=GovernanceAutoResolutionDecisionType.AUTO_RETRY_SAFE_APPLY).count(),
            'auto_require_followup': GovernanceAutoResolutionDecision.objects.filter(decision_type=GovernanceAutoResolutionDecisionType.AUTO_REQUIRE_FOLLOWUP).count(),
            'do_not_auto_resolve': GovernanceAutoResolutionDecision.objects.filter(decision_type=GovernanceAutoResolutionDecisionType.DO_NOT_AUTO_RESOLVE).count(),
        },
    }
