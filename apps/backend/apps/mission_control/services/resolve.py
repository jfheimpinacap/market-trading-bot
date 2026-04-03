from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from apps.mission_control.models import (
    AutonomousResumeDecision,
    AutonomousSessionAdmissionDecision,
    AutonomousSessionInterventionDecision,
    GovernanceReviewItem,
    GovernanceReviewItemStatus,
    GovernanceReviewResolution,
    GovernanceReviewResolutionStatus,
    GovernanceReviewResolutionType,
    GovernanceReviewSourceType,
)
from apps.mission_control.services.session_admission import apply_admission_decision
from apps.mission_control.services.session_health import apply_intervention
from apps.mission_control.services.session_recovery import apply_session_resume
from apps.portfolio_governor.models import PortfolioExposureApplyDecision, PortfolioExposureDecision
from apps.portfolio_governor.services.apply_record import execute_apply_decision
from apps.portfolio_governor.services.run import apply_exposure_decision
from apps.runtime_governor.models import RuntimeFeedbackApplyDecision, RuntimeModeTransitionDecision
from apps.runtime_governor.runtime_feedback_apply.services.apply import apply_runtime_feedback_apply_decision
from apps.runtime_governor.services.apply_transition import apply_stabilized_transition_decision


@dataclass
class ResolutionExecution:
    status: str
    summary: str
    metadata: dict


def _to_resolution_status(raw: str | None) -> str:
    value = (raw or '').upper()
    if value in {GovernanceReviewResolutionStatus.APPLIED, GovernanceReviewResolutionStatus.SKIPPED, GovernanceReviewResolutionStatus.BLOCKED, GovernanceReviewResolutionStatus.FAILED}:
        return value
    if value in {'PROPOSED', 'OPEN', 'IN_REVIEW'}:
        return GovernanceReviewResolutionStatus.SKIPPED
    return GovernanceReviewResolutionStatus.BLOCKED


def _safe_manual_apply(item: GovernanceReviewItem) -> ResolutionExecution:
    if item.source_type == GovernanceReviewSourceType.SESSION_HEALTH:
        decision = AutonomousSessionInterventionDecision.objects.get(pk=item.source_object_id)
        record = apply_intervention(decision=decision, automatic=False)
        return ResolutionExecution(
            status=_to_resolution_status(record.intervention_status if record else decision.decision_status),
            summary=(record.intervention_summary if record else 'Session health decision reviewed manually.'),
            metadata={'decision_id': decision.id, 'intervention_record_id': record.id if record else None},
        )

    if item.source_type == GovernanceReviewSourceType.SESSION_RECOVERY:
        decision = AutonomousResumeDecision.objects.get(pk=item.source_object_id)
        result = apply_session_resume(decision=decision, automatic=False)
        return ResolutionExecution(
            status=_to_resolution_status(result.record.resume_status),
            summary=result.record.resume_summary,
            metadata={'decision_id': decision.id, 'resume_record_id': result.record.id, 'applied_mode': result.record.applied_mode},
        )

    if item.source_type == GovernanceReviewSourceType.SESSION_ADMISSION:
        decision = AutonomousSessionAdmissionDecision.objects.get(pk=item.source_object_id)
        applied = apply_admission_decision(decision=decision, automatic=False)
        status = GovernanceReviewResolutionStatus.APPLIED if applied.decision_status == 'PROPOSED' else _to_resolution_status(applied.decision_status)
        return ResolutionExecution(
            status=status,
            summary='Session admission decision reviewed with manual operator approval.',
            metadata={'decision_id': decision.id, 'decision_status': applied.decision_status},
        )

    if item.source_type == GovernanceReviewSourceType.MODE_FEEDBACK_APPLY:
        decision = RuntimeFeedbackApplyDecision.objects.get(pk=item.source_object_id)
        result = apply_runtime_feedback_apply_decision(apply_decision=decision, triggered_by='mission-control-governance-resolution')
        return ResolutionExecution(
            status=_to_resolution_status(result.apply_decision.apply_status),
            summary=result.apply_record.record_summary,
            metadata={'apply_decision_id': decision.id, 'apply_record_id': result.apply_record.id},
        )

    if item.source_type == GovernanceReviewSourceType.MODE_STABILIZATION:
        decision = RuntimeModeTransitionDecision.objects.get(pk=item.source_object_id)
        result = apply_stabilized_transition_decision(
            transition_decision=decision,
            triggered_by='mission-control-governance-resolution',
            auto_apply_safe=False,
        )
        return ResolutionExecution(
            status=_to_resolution_status(result.apply_record.apply_status),
            summary=result.apply_record.apply_summary,
            metadata={'transition_decision_id': decision.id, 'transition_apply_record_id': result.apply_record.id},
        )

    if item.source_type == GovernanceReviewSourceType.EXPOSURE_COORDINATION:
        decision = PortfolioExposureDecision.objects.get(pk=item.source_object_id)
        run = apply_exposure_decision(decision=decision, force_apply=False, triggered_by='mission-control-governance-resolution')
        apply_decision = PortfolioExposureApplyDecision.objects.filter(linked_apply_run=run, linked_exposure_decision=decision).order_by('-created_at_decision', '-id').first()
        return ResolutionExecution(
            status=_to_resolution_status(apply_decision.apply_status if apply_decision else 'BLOCKED'),
            summary='Portfolio exposure decision routed through conservative apply bridge.',
            metadata={'decision_id': decision.id, 'apply_run_id': run.id, 'apply_decision_id': apply_decision.id if apply_decision else None},
        )

    if item.source_type == GovernanceReviewSourceType.EXPOSURE_APPLY:
        apply_decision = PortfolioExposureApplyDecision.objects.get(pk=item.source_object_id)
        record = execute_apply_decision(apply_decision=apply_decision, force_apply=False)
        return ResolutionExecution(
            status=_to_resolution_status(record.record_status),
            summary=record.record_summary,
            metadata={'apply_decision_id': apply_decision.id, 'apply_record_id': record.id},
        )

    return ResolutionExecution(
        status=GovernanceReviewResolutionStatus.BLOCKED,
        summary='No safe manual apply path is available for this governance source.',
        metadata={'source_type': item.source_type},
    )


def _retry_safe_apply(item: GovernanceReviewItem) -> ResolutionExecution:
    if item.source_type != GovernanceReviewSourceType.SESSION_RECOVERY:
        return ResolutionExecution(
            status=GovernanceReviewResolutionStatus.BLOCKED,
            summary='Retry safe apply is only enabled for session recovery safe-resume decisions.',
            metadata={'source_type': item.source_type},
        )

    decision = AutonomousResumeDecision.objects.get(pk=item.source_object_id)
    result = apply_session_resume(decision=decision, automatic=True)
    return ResolutionExecution(
        status=_to_resolution_status(result.record.resume_status),
        summary=result.record.resume_summary,
        metadata={'decision_id': decision.id, 'resume_record_id': result.record.id, 'applied_mode': result.record.applied_mode},
    )


@transaction.atomic
def resolve_governance_review_item(
    *,
    item: GovernanceReviewItem,
    resolution_type: str,
    resolution_summary: str = '',
    metadata: dict | None = None,
) -> GovernanceReviewResolution:
    execution: ResolutionExecution

    if resolution_type == GovernanceReviewResolutionType.DISMISS_AS_EXPECTED:
        item.item_status = GovernanceReviewItemStatus.DISMISSED
        item.save(update_fields=['item_status', 'updated_at'])
        execution = ResolutionExecution(
            status=GovernanceReviewResolutionStatus.SKIPPED,
            summary='Item dismissed as expected; retained for governance audit trail.',
            metadata={'closed_as': 'dismissed_expected'},
        )
    elif resolution_type == GovernanceReviewResolutionType.KEEP_BLOCKED:
        item.item_status = GovernanceReviewItemStatus.RESOLVED
        item.save(update_fields=['item_status', 'updated_at'])
        execution = ResolutionExecution(
            status=GovernanceReviewResolutionStatus.BLOCKED,
            summary='Item closed and explicitly kept blocked by operator decision.',
            metadata={'closed_as': 'resolved_blocked'},
        )
    elif resolution_type == GovernanceReviewResolutionType.REQUIRE_FOLLOWUP:
        item.item_status = GovernanceReviewItemStatus.RESOLVED
        item.save(update_fields=['item_status', 'updated_at'])
        execution = ResolutionExecution(
            status=GovernanceReviewResolutionStatus.SKIPPED,
            summary='Item closed with explicit follow-up requirement.',
            metadata={'followup_required': True},
        )
    elif resolution_type == GovernanceReviewResolutionType.RETRY_SAFE_APPLY:
        execution = _retry_safe_apply(item)
        item.item_status = GovernanceReviewItemStatus.RESOLVED if execution.status in {
            GovernanceReviewResolutionStatus.APPLIED,
            GovernanceReviewResolutionStatus.SKIPPED,
            GovernanceReviewResolutionStatus.BLOCKED,
        } else GovernanceReviewItemStatus.OPEN
        item.save(update_fields=['item_status', 'updated_at'])
    else:
        execution = _safe_manual_apply(item)
        item.item_status = GovernanceReviewItemStatus.RESOLVED if execution.status in {
            GovernanceReviewResolutionStatus.APPLIED,
            GovernanceReviewResolutionStatus.SKIPPED,
            GovernanceReviewResolutionStatus.BLOCKED,
        } else GovernanceReviewItemStatus.OPEN
        item.save(update_fields=['item_status', 'updated_at'])

    return GovernanceReviewResolution.objects.create(
        linked_review_item=item,
        resolution_type=resolution_type,
        resolution_status=execution.status,
        resolution_summary=resolution_summary or execution.summary,
        metadata={**(metadata or {}), **execution.metadata},
    )
