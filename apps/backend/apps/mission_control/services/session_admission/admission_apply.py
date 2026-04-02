from __future__ import annotations

from apps.mission_control.models import (
    AutonomousRuntimeSessionStatus,
    AutonomousSessionAdmissionDecision,
    AutonomousSessionAdmissionDecisionStatus,
    AutonomousSessionAdmissionDecisionType,
)


def apply_admission_decision(*, decision: AutonomousSessionAdmissionDecision, automatic: bool = True) -> AutonomousSessionAdmissionDecision:
    session = decision.linked_session
    if decision.decision_status not in {
        AutonomousSessionAdmissionDecisionStatus.PROPOSED,
        AutonomousSessionAdmissionDecisionStatus.SKIPPED,
    }:
        return decision

    if decision.decision_type == AutonomousSessionAdmissionDecisionType.PAUSE_SESSION:
        session.session_status = AutonomousRuntimeSessionStatus.PAUSED
    elif decision.decision_type in {AutonomousSessionAdmissionDecisionType.PARK_SESSION, AutonomousSessionAdmissionDecisionType.DEFER_SESSION}:
        session.metadata = {**session.metadata, 'admission_runtime_state': 'PARKED' if decision.decision_type == AutonomousSessionAdmissionDecisionType.PARK_SESSION else 'DEFERRED'}
    elif decision.decision_type == AutonomousSessionAdmissionDecisionType.RETIRE_SESSION:
        session.session_status = AutonomousRuntimeSessionStatus.COMPLETED
        session.metadata = {**session.metadata, 'admission_runtime_state': 'RETIRED'}
    elif decision.decision_type in {AutonomousSessionAdmissionDecisionType.ADMIT_SESSION, AutonomousSessionAdmissionDecisionType.ALLOW_RESUME}:
        session.session_status = AutonomousRuntimeSessionStatus.RUNNING
        session.metadata = {**session.metadata, 'admission_runtime_state': 'ADMITTED'}
    else:
        decision.decision_status = AutonomousSessionAdmissionDecisionStatus.BLOCKED
        decision.metadata = {**decision.metadata, 'apply': 'manual_review_required', 'automatic': automatic}
        decision.save(update_fields=['decision_status', 'metadata', 'updated_at'])
        return decision

    session.save(update_fields=['session_status', 'metadata', 'updated_at'])
    decision.decision_status = AutonomousSessionAdmissionDecisionStatus.APPLIED if automatic else AutonomousSessionAdmissionDecisionStatus.PROPOSED
    decision.metadata = {**decision.metadata, 'automatic': automatic, 'applied_session_status': session.session_status}
    decision.save(update_fields=['decision_status', 'metadata', 'updated_at'])
    return decision
