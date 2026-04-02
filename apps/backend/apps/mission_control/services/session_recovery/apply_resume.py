from __future__ import annotations

from dataclasses import dataclass

from apps.mission_control.models import (
    AutonomousRecoveryBlocker,
    AutonomousRecoveryBlockerStatus,
    AutonomousResumeAppliedMode,
    AutonomousResumeDecision,
    AutonomousResumeDecisionStatus,
    AutonomousResumeDecisionType,
    AutonomousResumeRecord,
    AutonomousResumeRecordStatus,
    AutonomousRuntimeSessionStatus,
)
from apps.mission_control.services.session_heartbeat import get_runner_state, run_heartbeat_pass
from apps.mission_control.services.session_runtime.session import resume_autonomous_session
from apps.mission_control.services.session_timing import apply_schedule_profile, ensure_default_schedule_profiles, run_session_timing_review


@dataclass
class ResumeApplyResult:
    record: AutonomousResumeRecord
    session_resumed: bool


def _has_active_blockers(session_id: int) -> bool:
    return AutonomousRecoveryBlocker.objects.filter(
        linked_session_id=session_id,
        blocker_status=AutonomousRecoveryBlockerStatus.ACTIVE,
    ).exists()


def apply_resume_decision(
    *,
    decision: AutonomousResumeDecision,
    applied_mode: str = AutonomousResumeAppliedMode.MANUAL_RESUME,
    automatic: bool = False,
) -> ResumeApplyResult:
    session = decision.linked_session

    if automatic and (decision.decision_type != AutonomousResumeDecisionType.READY_TO_RESUME or not decision.auto_applicable):
        decision.decision_status = AutonomousResumeDecisionStatus.SKIPPED
        decision.save(update_fields=['decision_status', 'updated_at'])
        return ResumeApplyResult(
            record=AutonomousResumeRecord.objects.create(
                linked_session=session,
                linked_resume_decision=decision,
                resume_status=AutonomousResumeRecordStatus.SKIPPED,
                applied_mode=AutonomousResumeAppliedMode.AUTO_SAFE_RESUME,
                resume_summary='Safe auto-resume skipped because decision is not READY_TO_RESUME with auto_applicable=true.',
                metadata={'automatic': True},
            ),
            session_resumed=False,
        )

    if _has_active_blockers(session.id):
        decision.decision_status = AutonomousResumeDecisionStatus.BLOCKED
        decision.save(update_fields=['decision_status', 'updated_at'])
        return ResumeApplyResult(
            record=AutonomousResumeRecord.objects.create(
                linked_session=session,
                linked_resume_decision=decision,
                resume_status=AutonomousResumeRecordStatus.BLOCKED,
                applied_mode=applied_mode,
                resume_summary='Resume blocked by active recovery blockers.',
                metadata={'automatic': automatic},
            ),
            session_resumed=False,
        )

    if decision.decision_type not in {
        AutonomousResumeDecisionType.READY_TO_RESUME,
        AutonomousResumeDecisionType.RESUME_IN_MONITOR_ONLY_MODE,
    }:
        decision.decision_status = AutonomousResumeDecisionStatus.SKIPPED
        decision.save(update_fields=['decision_status', 'updated_at'])
        return ResumeApplyResult(
            record=AutonomousResumeRecord.objects.create(
                linked_session=session,
                linked_resume_decision=decision,
                resume_status=AutonomousResumeRecordStatus.SKIPPED,
                applied_mode=applied_mode,
                resume_summary='Decision is not a resume action; apply skipped.',
                metadata={'automatic': automatic},
            ),
            session_resumed=False,
        )

    if session.session_status in {AutonomousRuntimeSessionStatus.DEGRADED, AutonomousRuntimeSessionStatus.BLOCKED} and decision.decision_type == AutonomousResumeDecisionType.READY_TO_RESUME:
        decision.decision_status = AutonomousResumeDecisionStatus.BLOCKED
        decision.save(update_fields=['decision_status', 'updated_at'])
        return ResumeApplyResult(
            record=AutonomousResumeRecord.objects.create(
                linked_session=session,
                linked_resume_decision=decision,
                resume_status=AutonomousResumeRecordStatus.BLOCKED,
                applied_mode=applied_mode,
                resume_summary='Resume blocked: session is still degraded/blocked and requires conservative or manual recovery.',
                metadata={'automatic': automatic},
            ),
            session_resumed=False,
        )

    try:
        if decision.decision_type == AutonomousResumeDecisionType.RESUME_IN_MONITOR_ONLY_MODE:
            profiles = {profile.slug: profile for profile in ensure_default_schedule_profiles()}
            profile = profiles.get('monitor_heavy')
            if profile:
                apply_schedule_profile(session=session, profile=profile)
            session.runtime_mode = 'MONITOR_ONLY'
            session.save(update_fields=['runtime_mode', 'updated_at'])
            applied_mode = AutonomousResumeAppliedMode.MONITOR_ONLY_RESUME

        resume_autonomous_session(session)
        run_session_timing_review(session_ids=[session.id])

        runner_state = get_runner_state()
        if runner_state.runner_status == 'RUNNING':
            run_heartbeat_pass()

        decision.decision_status = AutonomousResumeDecisionStatus.APPLIED
        decision.save(update_fields=['decision_status', 'updated_at'])
        record = AutonomousResumeRecord.objects.create(
            linked_session=session,
            linked_resume_decision=decision,
            resume_status=AutonomousResumeRecordStatus.APPLIED,
            applied_mode=applied_mode,
            resume_summary='Session resumed safely and reintegrated with timing/heartbeat governance.',
            metadata={
                'automatic': automatic,
                'runner_status': runner_state.runner_status,
            },
        )
        return ResumeApplyResult(record=record, session_resumed=True)
    except Exception as exc:  # pragma: no cover
        decision.decision_status = AutonomousResumeDecisionStatus.BLOCKED
        decision.save(update_fields=['decision_status', 'updated_at'])
        return ResumeApplyResult(
            record=AutonomousResumeRecord.objects.create(
                linked_session=session,
                linked_resume_decision=decision,
                resume_status=AutonomousResumeRecordStatus.FAILED,
                applied_mode=applied_mode,
                resume_summary='Resume apply failed unexpectedly.',
                metadata={'automatic': automatic, 'error': str(exc)},
            ),
            session_resumed=False,
        )
