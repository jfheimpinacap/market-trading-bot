from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from apps.approval_center.models import ApprovalRequest, ApprovalRequestStatus
from apps.automation_policy.models import AutomationActionExecutionStatus, AutomationActionLog, AutomationDecision, AutomationDecisionOutcome
from apps.incident_commander.models import IncidentRecord
from apps.policy_rollout.models import PolicyBaselineSnapshot, PolicyRolloutRun
from apps.trust_calibration.services.metrics import build_snapshot_metrics


@dataclass
class SnapshotPayload:
    metrics: dict
    counts: dict


def collect_snapshot_payload(*, action_type: str, since) -> SnapshotPayload:
    approvals = ApprovalRequest.objects.filter(created_at__gte=since, metadata__action_type=action_type)
    approval_counts = approvals.aggregate(
        granted=Count('id', filter=Q(status=ApprovalRequestStatus.APPROVED)),
        rejected=Count('id', filter=Q(status=ApprovalRequestStatus.REJECTED)),
        expired=Count('id', filter=Q(status=ApprovalRequestStatus.EXPIRED)),
        escalated=Count('id', filter=Q(status=ApprovalRequestStatus.ESCALATED)),
    )
    retries = sum(int(item.metadata.get('retry_count') or 0) for item in approvals.only('metadata'))
    approval_overrides = sum(1 for item in approvals.only('metadata') if item.metadata.get('operator_override'))

    decisions = AutomationDecision.objects.filter(created_at__gte=since, action_type=action_type)
    blocked_decisions = decisions.filter(outcome=AutomationDecisionOutcome.BLOCKED).count()
    decision_overrides = sum(1 for item in decisions.only('metadata') if item.metadata.get('operator_override'))

    logs = AutomationActionLog.objects.filter(created_at__gte=since, decision__action_type=action_type).select_related('decision')
    auto_executed = logs.filter(execution_status__in=[AutomationActionExecutionStatus.EXECUTED, AutomationActionExecutionStatus.FAILED]).count()
    auto_failed = logs.filter(execution_status=AutomationActionExecutionStatus.FAILED).count()

    decision_ids = list(decisions.values_list('id', flat=True))
    incidents = IncidentRecord.objects.filter(created_at__gte=since, related_object_type='automation_decision', related_object_id__in=[str(item) for item in decision_ids]).count()

    metrics = build_snapshot_metrics(
        granted=approval_counts['granted'] or 0,
        rejected=approval_counts['rejected'] or 0,
        expired=approval_counts['expired'] or 0,
        escalated=approval_counts['escalated'] or 0,
        auto_executed=auto_executed,
        auto_failed=auto_failed,
        blocked=blocked_decisions,
        retries=retries,
        overrides=approval_overrides + decision_overrides,
        incidents=incidents,
    )

    counts = {
        'approvals_granted': approval_counts['granted'] or 0,
        'approvals_rejected': approval_counts['rejected'] or 0,
        'approvals_expired': approval_counts['expired'] or 0,
        'approvals_escalated': approval_counts['escalated'] or 0,
        'auto_actions_executed': auto_executed,
        'auto_actions_failed': auto_failed,
        'blocked_decisions': blocked_decisions,
        'retry_count': retries,
        'operator_overrides': approval_overrides + decision_overrides,
        'incidents_after_auto': incidents,
    }
    return SnapshotPayload(metrics=metrics, counts=counts)


def create_baseline_snapshot(run: PolicyRolloutRun) -> PolicyBaselineSnapshot:
    since = run.application_log.applied_at - timedelta(days=run.observation_window_days)
    payload = collect_snapshot_payload(action_type=run.policy_tuning_candidate.action_type, since=since)
    return PolicyBaselineSnapshot.objects.create(run=run, metrics=payload.metrics, counts=payload.counts)


def create_rollout_run(*, candidate, application_log, observation_window_days: int = 14, metadata: dict | None = None) -> PolicyRolloutRun:
    run = PolicyRolloutRun.objects.create(
        policy_tuning_candidate=candidate,
        application_log=application_log,
        observation_window_days=observation_window_days,
        summary='Observation window opened for applied policy tuning candidate.',
        metadata={
            **(metadata or {}),
            'manual_first': True,
            'paper_only': True,
            'started_at': timezone.now().isoformat(),
        },
    )
    create_baseline_snapshot(run)
    return run
