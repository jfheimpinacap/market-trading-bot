from collections import defaultdict
from datetime import timedelta

from django.utils import timezone

from apps.approval_center.models import ApprovalRequest, ApprovalRequestStatus
from apps.automation_policy.models import AutomationActionExecutionStatus, AutomationActionLog, AutomationDecision, AutomationDecisionOutcome, AutomationPolicyRule
from apps.incident_commander.models import IncidentRecord
from apps.trust_calibration.models import AutomationFeedbackSnapshot, TrustCalibrationRun
from apps.trust_calibration.services.metrics import build_snapshot_metrics


def _dict_key(*, action_type: str, source_type: str, runbook_template_slug: str, profile_slug: str) -> tuple[str, str, str, str]:
    return action_type or 'unknown_action', source_type or '', runbook_template_slug or '', profile_slug or ''


def consolidate_feedback(run: TrustCalibrationRun) -> list[AutomationFeedbackSnapshot]:
    since = run.started_at - timedelta(days=run.window_days)
    buckets: dict[tuple[str, str, str, str], dict] = defaultdict(lambda: {
        'approvals_granted': 0,
        'approvals_rejected': 0,
        'approvals_expired': 0,
        'approvals_escalated': 0,
        'auto_actions_executed': 0,
        'auto_actions_failed': 0,
        'blocked_decisions': 0,
        'retry_count': 0,
        'operator_overrides': 0,
        'incidents_after_auto': 0,
        'current_trust_tier': '',
        'metadata': {'approval_samples': [], 'decision_ids': [], 'trace_roots': []},
    })

    approvals = ApprovalRequest.objects.filter(created_at__gte=since)
    if run.source_type:
        approvals = approvals.filter(source_type=run.source_type)

    for approval in approvals.iterator():
        action_type = str(approval.metadata.get('action_type') or approval.metadata.get('automation_action_type') or approval.source_type)
        runbook_template_slug = str(approval.metadata.get('runbook_template_slug') or '')
        profile_slug = str(approval.metadata.get('policy_profile_slug') or '')
        key = _dict_key(action_type=action_type, source_type=approval.source_type, runbook_template_slug=runbook_template_slug, profile_slug=profile_slug)
        bucket = buckets[key]

        if approval.status == ApprovalRequestStatus.APPROVED:
            bucket['approvals_granted'] += 1
        elif approval.status == ApprovalRequestStatus.REJECTED:
            bucket['approvals_rejected'] += 1
        elif approval.status == ApprovalRequestStatus.EXPIRED:
            bucket['approvals_expired'] += 1
        elif approval.status == ApprovalRequestStatus.ESCALATED:
            bucket['approvals_escalated'] += 1

        retries = int(approval.metadata.get('retry_count') or 0)
        bucket['retry_count'] += max(retries, 0)
        if approval.metadata.get('operator_override'):
            bucket['operator_overrides'] += 1
        if approval.metadata.get('trace'):
            bucket['metadata']['trace_roots'].append(approval.metadata.get('trace'))
        bucket['metadata']['approval_samples'].append({'id': approval.id, 'status': approval.status, 'source_object_id': approval.source_object_id})

    decisions = AutomationDecision.objects.filter(created_at__gte=since)
    if run.profile_slug:
        decisions = decisions.filter(profile__slug=run.profile_slug)

    for decision in decisions.iterator():
        runbook_template_slug = str(decision.metadata.get('runbook_template_slug') or '')
        source_type = str(decision.metadata.get('source_type') or decision.source_context_type or '')
        profile_slug = decision.profile.slug if decision.profile else ''
        key = _dict_key(action_type=decision.action_type, source_type=source_type, runbook_template_slug=runbook_template_slug, profile_slug=profile_slug)
        bucket = buckets[key]

        if decision.outcome == AutomationDecisionOutcome.BLOCKED:
            bucket['blocked_decisions'] += 1
        if decision.metadata.get('operator_override'):
            bucket['operator_overrides'] += 1
        bucket['metadata']['decision_ids'].append(decision.id)
        bucket['current_trust_tier'] = decision.effective_trust_tier

    action_logs = AutomationActionLog.objects.filter(created_at__gte=since).select_related('decision', 'decision__profile')
    if run.profile_slug:
        action_logs = action_logs.filter(decision__profile__slug=run.profile_slug)

    for log in action_logs.iterator():
        decision = log.decision
        runbook_template_slug = str(decision.metadata.get('runbook_template_slug') or '')
        source_type = str(decision.metadata.get('source_type') or decision.source_context_type or '')
        profile_slug = decision.profile.slug if decision.profile else ''
        key = _dict_key(action_type=decision.action_type, source_type=source_type, runbook_template_slug=runbook_template_slug, profile_slug=profile_slug)
        bucket = buckets[key]

        if log.execution_status == AutomationActionExecutionStatus.EXECUTED:
            bucket['auto_actions_executed'] += 1
        elif log.execution_status == AutomationActionExecutionStatus.FAILED:
            bucket['auto_actions_executed'] += 1
            bucket['auto_actions_failed'] += 1

    incident_counts = defaultdict(int)
    for incident in IncidentRecord.objects.filter(created_at__gte=since, related_object_type='automation_decision').iterator():
        try:
            decision = AutomationDecision.objects.filter(pk=int(incident.related_object_id)).first()
        except (TypeError, ValueError):
            decision = None
        if not decision:
            continue
        key = _dict_key(
            action_type=decision.action_type,
            source_type=str(decision.metadata.get('source_type') or decision.source_context_type or ''),
            runbook_template_slug=str(decision.metadata.get('runbook_template_slug') or ''),
            profile_slug=decision.profile.slug if decision.profile else '',
        )
        incident_counts[key] += 1

    snapshots: list[AutomationFeedbackSnapshot] = []
    for key, values in buckets.items():
        action_type, source_type, runbook_template_slug, profile_slug = key
        current_tier = values['current_trust_tier']
        if not current_tier:
            rule = AutomationPolicyRule.objects.filter(action_type=action_type).order_by('-created_at').first()
            current_tier = rule.trust_tier if rule else ''

        values['incidents_after_auto'] = incident_counts.get(key, 0)
        metrics = build_snapshot_metrics(
            granted=values['approvals_granted'],
            rejected=values['approvals_rejected'],
            expired=values['approvals_expired'],
            escalated=values['approvals_escalated'],
            auto_executed=values['auto_actions_executed'],
            auto_failed=values['auto_actions_failed'],
            blocked=values['blocked_decisions'],
            retries=values['retry_count'],
            overrides=values['operator_overrides'],
            incidents=values['incidents_after_auto'],
        )

        snapshots.append(AutomationFeedbackSnapshot.objects.create(
            run=run,
            action_type=action_type,
            source_type=source_type,
            runbook_template_slug=runbook_template_slug,
            profile_slug=profile_slug,
            current_trust_tier=current_tier,
            approvals_granted=values['approvals_granted'],
            approvals_rejected=values['approvals_rejected'],
            approvals_expired=values['approvals_expired'],
            approvals_escalated=values['approvals_escalated'],
            auto_actions_executed=values['auto_actions_executed'],
            auto_actions_failed=values['auto_actions_failed'],
            blocked_decisions=values['blocked_decisions'],
            retry_count=values['retry_count'],
            operator_overrides=values['operator_overrides'],
            incidents_after_auto=values['incidents_after_auto'],
            metrics=metrics,
            metadata=values['metadata'],
        ))

    run.finished_at = timezone.now()
    run.status = 'READY'
    run.summary = f'Analyzed {len(snapshots)} action domains over the last {run.window_days} days.'
    run.save(update_fields=['finished_at', 'status', 'summary', 'updated_at'])
    return snapshots
