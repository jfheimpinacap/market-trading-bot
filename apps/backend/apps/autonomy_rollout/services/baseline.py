from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from apps.approval_center.models import ApprovalRequest, ApprovalRequestStatus, ApprovalSourceType
from apps.automation_policy.models import AutomationActionExecutionStatus, AutomationActionLog, AutomationDecision, AutomationDecisionOutcome
from apps.autonomy_rollout.models import AutonomyBaselineSnapshot, AutonomyRolloutRun
from apps.incident_commander.models import DegradedModeState, IncidentRecord
from apps.trust_calibration.services.metrics import safe_rate


@dataclass
class SnapshotPayload:
    metrics: dict
    counts: dict


def _stringify_rates(values: dict) -> dict:
    return {key: (str(value) if hasattr(value, 'quantize') else value) for key, value in values.items()}


def collect_snapshot_payload(*, action_types: list[str], source_apps: list[str], since) -> SnapshotPayload:
    approvals = ApprovalRequest.objects.filter(created_at__gte=since, metadata__action_type__in=action_types)
    approval_counts = approvals.aggregate(
        granted=Count('id', filter=Q(status=ApprovalRequestStatus.APPROVED)),
        rejected=Count('id', filter=Q(status=ApprovalRequestStatus.REJECTED)),
        expired=Count('id', filter=Q(status=ApprovalRequestStatus.EXPIRED)),
        escalated=Count('id', filter=Q(status=ApprovalRequestStatus.ESCALATED)),
    )

    runbook_pauses = approvals.filter(source_type=ApprovalSourceType.RUNBOOK_CHECKPOINT, status__in=[ApprovalRequestStatus.PENDING, ApprovalRequestStatus.ESCALATED]).count()

    decisions = AutomationDecision.objects.filter(created_at__gte=since, action_type__in=action_types)
    decision_count = decisions.count()
    blocked_decisions = decisions.filter(outcome=AutomationDecisionOutcome.BLOCKED).count()

    logs = AutomationActionLog.objects.filter(created_at__gte=since, decision__action_type__in=action_types).select_related('decision')
    auto_executed = logs.filter(execution_status__in=[AutomationActionExecutionStatus.EXECUTED, AutomationActionExecutionStatus.FAILED]).count()
    auto_failed = logs.filter(execution_status=AutomationActionExecutionStatus.FAILED).count()

    decision_ids = list(decisions.values_list('id', flat=True))
    incidents = IncidentRecord.objects.filter(created_at__gte=since, related_object_type='automation_decision', related_object_id__in=[str(item) for item in decision_ids])
    domain_incidents = incidents.count()
    cross_domain_incidents = IncidentRecord.objects.filter(created_at__gte=since, source_app__in=source_apps).exclude(related_object_id__in=[str(item) for item in decision_ids]).count()

    degraded_events = DegradedModeState.objects.filter(created_at__gte=since)
    degraded_with_domain = sum(1 for item in degraded_events.only('degraded_modules') if any(app in (item.degraded_modules or []) for app in source_apps))

    granted = approval_counts['granted'] or 0
    rejected = approval_counts['rejected'] or 0
    expired = approval_counts['expired'] or 0
    escalated = approval_counts['escalated'] or 0
    total_approvals = granted + rejected + expired + escalated
    sample_size = total_approvals + auto_executed

    metrics = _stringify_rates({
        'sample_size': sample_size,
        'approval_rate': safe_rate(granted, total_approvals),
        'rejection_rate': safe_rate(rejected, total_approvals),
        'escalation_rate': safe_rate(escalated, total_approvals),
        'expiry_rate': safe_rate(expired, total_approvals),
        'auto_execution_success_rate': safe_rate(max(auto_executed - auto_failed, 0), max(auto_executed, 1)),
        'approval_friction_score': safe_rate(rejected + expired + escalated + blocked_decisions, max(total_approvals + blocked_decisions, 1)),
        'blocked_rate': safe_rate(blocked_decisions, max(decision_count, 1)),
        'incident_after_auto_rate': safe_rate(domain_incidents, max(auto_executed, 1)),
        'manual_intervention_rate': safe_rate(granted + rejected + blocked_decisions, max(sample_size, 1)),
        'runbook_autopilot_pause_rate': safe_rate(runbook_pauses, max(total_approvals, 1)),
        'degraded_context_rate': safe_rate(degraded_with_domain, max(degraded_events.count(), 1)),
    })

    counts = {
        'approvals_granted': granted,
        'approvals_rejected': rejected,
        'approvals_expired': expired,
        'approvals_escalated': escalated,
        'auto_actions_executed': auto_executed,
        'auto_actions_failed': auto_failed,
        'blocked_decisions': blocked_decisions,
        'incidents_after_auto': domain_incidents,
        'runbook_autopilot_pauses': runbook_pauses,
        'degraded_events': degraded_with_domain,
        'cross_domain_incidents': cross_domain_incidents,
    }
    return SnapshotPayload(metrics=metrics, counts=counts)


def create_baseline_snapshot(run: AutonomyRolloutRun) -> AutonomyBaselineSnapshot:
    since = run.autonomy_stage_transition.applied_at - timedelta(days=run.observation_window_days)
    payload = collect_snapshot_payload(action_types=list(run.domain.action_types or []), source_apps=list(run.domain.source_apps or []), since=since)
    return AutonomyBaselineSnapshot.objects.create(run=run, metrics=payload.metrics, counts=payload.counts)


def create_rollout_run(*, transition, observation_window_days: int = 14, metadata: dict | None = None) -> AutonomyRolloutRun:
    run = AutonomyRolloutRun.objects.create(
        autonomy_stage_transition=transition,
        domain=transition.domain,
        observation_window_days=observation_window_days,
        summary='Observation window opened for applied autonomy domain transition.',
        metadata={
            **(metadata or {}),
            'manual_first': True,
            'paper_only': True,
            'started_at': timezone.now().isoformat(),
            'previous_stage': transition.previous_stage,
            'applied_stage': transition.applied_stage,
        },
    )
    create_baseline_snapshot(run)
    return run
