from __future__ import annotations

from dataclasses import dataclass

from apps.mission_control.models import (
    AutonomousResumeApplyMode,
    AutonomousResumeDecision,
    AutonomousResumeDecisionStatus,
    AutonomousResumeDecisionType,
    AutonomousResumeRecord,
    AutonomousResumeStatus,
)
from apps.mission_control.services.session_recovery.recovery_blockers import detect_recovery_blockers
from apps.mission_control.services.session_runtime.session import resume_autonomous_session
from apps.mission_control.services.session_timing.timing import evaluate_session_timing


@dataclass
class ResumeApplyResult:
    decision: AutonomousResumeDecision
    record: AutonomousResumeRecord


def apply_session_resume(*, decision: AutonomousResumeDecision, automatic: bool = False) -> ResumeApplyResult:
    session = decision.linked_session
    blockers = detect_recovery_blockers(snapshot=decision.linked_recovery_snapshot)

    if blockers:
        decision.decision_status = AutonomousResumeDecisionStatus.BLOCKED
        decision.save(update_fields=['decision_status', 'updated_at'])
        record = AutonomousResumeRecord.objects.create(
            linked_session=session,
            linked_resume_decision=decision,
            resume_status=AutonomousResumeStatus.BLOCKED,
            applied_mode=AutonomousResumeApplyMode.AUTO_SAFE_RESUME if automatic else AutonomousResumeApplyMode.MANUAL_RESUME,
            resume_summary='Resume blocked because active recovery blockers are still present.',
            metadata={
                'automatic': automatic,
                'blocker_ids': [blocker.id for blocker in blockers],
                'blocker_types': [blocker.blocker_type for blocker in blockers],
            },
        )
        return ResumeApplyResult(decision=decision, record=record)

    if automatic and not (
        decision.decision_type == AutonomousResumeDecisionType.READY_TO_RESUME and decision.auto_applicable
    ):
        decision.decision_status = AutonomousResumeDecisionStatus.SKIPPED
        decision.save(update_fields=['decision_status', 'updated_at'])
        record = AutonomousResumeRecord.objects.create(
            linked_session=session,
            linked_resume_decision=decision,
            resume_status=AutonomousResumeStatus.SKIPPED,
            applied_mode=AutonomousResumeApplyMode.AUTO_SAFE_RESUME,
            resume_summary='Auto safe resume skipped because decision is not eligible for automatic apply.',
            metadata={'automatic': True, 'decision_type': decision.decision_type, 'auto_applicable': decision.auto_applicable},
        )
        return ResumeApplyResult(decision=decision, record=record)

    mode = AutonomousResumeApplyMode.AUTO_SAFE_RESUME if automatic else AutonomousResumeApplyMode.MANUAL_RESUME

    if decision.decision_type == AutonomousResumeDecisionType.RESUME_IN_MONITOR_ONLY_MODE:
        mode = AutonomousResumeApplyMode.MONITOR_ONLY_RESUME

    try:
        if decision.decision_type in {
            AutonomousResumeDecisionType.READY_TO_RESUME,
            AutonomousResumeDecisionType.RESUME_IN_MONITOR_ONLY_MODE,
        }:
            resume_autonomous_session(session)
            evaluate_session_timing(session=session)
            session.metadata = {
                **(session.metadata or {}),
                'resume_apply_mode': mode,
                'last_resume_decision_id': decision.id,
            }
            session.save(update_fields=['metadata', 'updated_at'])

            decision.decision_status = AutonomousResumeDecisionStatus.SKIPPED
            decision.save(update_fields=['decision_status', 'updated_at'])
            record = AutonomousResumeRecord.objects.create(
                linked_session=session,
                linked_resume_decision=decision,
                resume_status=AutonomousResumeStatus.APPLIED,
                applied_mode=mode,
                resume_summary=(
                    'Session resumed in monitor-only mode with conservative timing-policy reintegration.'
                    if mode == AutonomousResumeApplyMode.MONITOR_ONLY_RESUME
                    else 'Session resumed with conservative timing-policy/heartbeat reintegration.'
                ),
                metadata={'automatic': automatic, 'decision_type': decision.decision_type},
            )
            return ResumeApplyResult(decision=decision, record=record)

        decision.decision_status = AutonomousResumeDecisionStatus.BLOCKED
        decision.save(update_fields=['decision_status', 'updated_at'])
        record = AutonomousResumeRecord.objects.create(
            linked_session=session,
            linked_resume_decision=decision,
            resume_status=AutonomousResumeStatus.BLOCKED,
            applied_mode=mode,
            resume_summary='Resume decision requires manual review/escalation and cannot be applied directly.',
            metadata={'automatic': automatic, 'decision_type': decision.decision_type},
        )
        return ResumeApplyResult(decision=decision, record=record)
    except Exception as exc:  # pragma: no cover
        decision.decision_status = AutonomousResumeDecisionStatus.BLOCKED
        decision.save(update_fields=['decision_status', 'updated_at'])
        record = AutonomousResumeRecord.objects.create(
            linked_session=session,
            linked_resume_decision=decision,
            resume_status=AutonomousResumeStatus.FAILED,
            applied_mode=mode,
            resume_summary='Resume apply failed during execution.',
            metadata={'automatic': automatic, 'error': str(exc)},
        )
        return ResumeApplyResult(decision=decision, record=record)
