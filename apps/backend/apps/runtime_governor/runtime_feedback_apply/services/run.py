from __future__ import annotations

from collections import Counter

from django.utils import timezone

from apps.runtime_governor.models import (
    RuntimeFeedbackApplyDecision,
    RuntimeFeedbackApplyRecord,
    RuntimeFeedbackApplyRecommendation,
    RuntimeFeedbackApplyRun,
    RuntimeFeedbackDecision,
)
from apps.runtime_governor.runtime_feedback_apply.services.apply import (
    apply_runtime_feedback_apply_decision,
    build_apply_decision,
)
from apps.runtime_governor.runtime_feedback_apply.services.recommendation import emit_apply_recommendations


def run_runtime_feedback_apply_review(*, triggered_by: str = 'operator-ui', auto_apply: bool = False) -> dict:
    run = RuntimeFeedbackApplyRun.objects.create(metadata={'triggered_by': triggered_by, 'auto_apply': auto_apply})
    feedback_decisions = RuntimeFeedbackDecision.objects.order_by('-created_at', '-id')[:20]

    apply_decisions: list[RuntimeFeedbackApplyDecision] = []
    apply_records: list[RuntimeFeedbackApplyRecord] = []
    recommendations: list[RuntimeFeedbackApplyRecommendation] = []

    for feedback_decision in feedback_decisions:
        apply_decision = build_apply_decision(feedback_decision=feedback_decision, apply_run_id=run.id)
        apply_decisions.append(apply_decision)
        recommendations.extend(emit_apply_recommendations(apply_decision=apply_decision))

        if auto_apply and apply_decision.auto_applicable:
            apply_result = apply_runtime_feedback_apply_decision(
                apply_decision=apply_decision,
                triggered_by='runtime-feedback-apply-run',
            )
            apply_records.append(apply_result.apply_record)

    statuses = Counter(RuntimeFeedbackApplyDecision.objects.filter(linked_apply_run=run).values_list('apply_status', flat=True))
    record_statuses = Counter(RuntimeFeedbackApplyRecord.objects.filter(linked_apply_decision__linked_apply_run=run).values_list('record_status', flat=True))

    run.considered_feedback_decision_count = len(apply_decisions)
    run.applied_count = statuses.get('APPLIED', 0)
    run.manual_review_count = len([d for d in apply_decisions if d.apply_type == 'APPLY_MANUAL_REVIEW_ONLY'])
    run.blocked_count = statuses.get('BLOCKED', 0)
    run.mode_switch_count = len([r for r in apply_records if r.previous_mode != r.applied_mode and r.record_status == 'APPLIED'])
    run.enforcement_refresh_count = len([r for r in apply_records if r.enforcement_refreshed])
    run.recommendation_summary = {
        'count': len(recommendations),
        'latest_type': recommendations[0].recommendation_type if recommendations else None,
        'record_status_counts': dict(record_statuses),
    }
    run.metadata = {
        **(run.metadata or {}),
        'apply_decision_ids': [decision.id for decision in apply_decisions],
        'applied_record_ids': [record.id for record in apply_records],
    }
    run.completed_at = timezone.now()
    run.save()

    return {
        'run': run,
        'apply_decisions': apply_decisions,
        'apply_records': apply_records,
        'recommendations': recommendations,
    }


def apply_feedback_decision_by_id(*, feedback_decision: RuntimeFeedbackDecision, triggered_by: str = 'operator-ui') -> dict:
    apply_decision = build_apply_decision(feedback_decision=feedback_decision)
    recommendations = emit_apply_recommendations(apply_decision=apply_decision)
    result = apply_runtime_feedback_apply_decision(apply_decision=apply_decision, triggered_by=triggered_by)
    return {
        'apply_decision': result.apply_decision,
        'apply_record': result.apply_record,
        'recommendations': recommendations,
    }


def get_runtime_feedback_apply_summary() -> dict:
    latest_run = RuntimeFeedbackApplyRun.objects.order_by('-started_at', '-id').first()
    latest_apply_decision = RuntimeFeedbackApplyDecision.objects.order_by('-created_at', '-id').first()
    latest_record = RuntimeFeedbackApplyRecord.objects.order_by('-created_at', '-id').first()

    return {
        'latest_run_id': latest_run.id if latest_run else None,
        'latest_apply_decision_id': latest_apply_decision.id if latest_apply_decision else None,
        'latest_apply_record_id': latest_record.id if latest_record else None,
        'apply_runs': RuntimeFeedbackApplyRun.objects.count(),
        'apply_decisions': RuntimeFeedbackApplyDecision.objects.count(),
        'apply_records': RuntimeFeedbackApplyRecord.objects.count(),
        'recommendations': RuntimeFeedbackApplyRecommendation.objects.count(),
        'applied_count': RuntimeFeedbackApplyDecision.objects.filter(apply_status='APPLIED').count(),
        'manual_review_count': RuntimeFeedbackApplyDecision.objects.filter(apply_type='APPLY_MANUAL_REVIEW_ONLY').count(),
        'blocked_count': RuntimeFeedbackApplyDecision.objects.filter(apply_status='BLOCKED').count(),
        'enforcement_refresh_count': RuntimeFeedbackApplyRecord.objects.filter(enforcement_refreshed=True).count(),
        'recommendation_summary': latest_run.recommendation_summary if latest_run else {},
    }
