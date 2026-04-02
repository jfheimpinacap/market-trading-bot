from __future__ import annotations

from apps.mission_control.models import (
    AutonomousSessionAnomaly,
    AutonomousSessionAnomalySeverity,
    AutonomousSessionAnomalyType,
    AutonomousSessionHealthSnapshot,
    AutonomousSessionInterventionDecision,
    AutonomousSessionInterventionDecisionStatus,
    AutonomousSessionInterventionDecisionType,
    AutonomousSessionInterventionRecord,
    AutonomousSessionInterventionStatus,
)
from apps.mission_control.services.session_runtime.session import (
    pause_autonomous_session,
    resume_autonomous_session,
    stop_autonomous_session,
)


def decide_intervention(*, snapshot: AutonomousSessionHealthSnapshot, anomalies: list[AutonomousSessionAnomaly]) -> AutonomousSessionInterventionDecision:
    anomaly_types = {item.anomaly_type for item in anomalies}
    has_critical = any(item.anomaly_severity == AutonomousSessionAnomalySeverity.CRITICAL for item in anomalies)
    session = snapshot.linked_session

    decision_type = AutonomousSessionInterventionDecisionType.KEEP_RUNNING
    auto_applicable = False
    reason_codes = list(snapshot.reason_codes or [])

    if AutonomousSessionAnomalyType.SAFETY_OR_RUNTIME_PRESSURE in anomaly_types:
        decision_type = AutonomousSessionInterventionDecisionType.STOP_SESSION
        auto_applicable = True
        reason_codes.append('force_stop_safety_runtime')
    elif AutonomousSessionAnomalyType.RUNNER_SESSION_MISMATCH in anomaly_types and session.session_status == 'RUNNING':
        decision_type = AutonomousSessionInterventionDecisionType.PAUSE_SESSION
        auto_applicable = True
        reason_codes.append('pause_runner_mismatch')
    elif AutonomousSessionAnomalyType.INCIDENT_ESCALATION_PRESSURE in anomaly_types:
        decision_type = AutonomousSessionInterventionDecisionType.ESCALATE_TO_INCIDENT_REVIEW
        reason_codes.append('incident_escalation_preferred')
    elif AutonomousSessionAnomalyType.REPEATED_BLOCKED_TICKS in anomaly_types:
        decision_type = AutonomousSessionInterventionDecisionType.STOP_SESSION if has_critical else AutonomousSessionInterventionDecisionType.REQUIRE_MANUAL_REVIEW
        auto_applicable = has_critical
        reason_codes.append('persistent_blocked_ticks')
    elif AutonomousSessionAnomalyType.REPEATED_FAILED_TICKS in anomaly_types:
        decision_type = AutonomousSessionInterventionDecisionType.PAUSE_SESSION
        reason_codes.append('stabilize_failed_ticks')
    elif AutonomousSessionAnomalyType.PERSISTENT_PAUSE in anomaly_types and not snapshot.metadata.get('hard_block'):
        decision_type = AutonomousSessionInterventionDecisionType.RESUME_SESSION
        auto_applicable = True
        reason_codes.append('recoverable_pause')
    elif AutonomousSessionAnomalyType.STALE_SESSION_NO_PROGRESS in anomaly_types:
        decision_type = AutonomousSessionInterventionDecisionType.REQUIRE_MANUAL_REVIEW
        reason_codes.append('stalled_manual_review')

    summary = f'Intervention={decision_type} for session={session.id} with {len(anomalies)} anomalies.'
    return AutonomousSessionInterventionDecision.objects.create(
        linked_session=session,
        linked_health_snapshot=snapshot,
        decision_type=decision_type,
        decision_status=AutonomousSessionInterventionDecisionStatus.PROPOSED,
        auto_applicable=auto_applicable,
        decision_summary=summary,
        reason_codes=list(dict.fromkeys(reason_codes)),
        metadata={'anomaly_types': sorted(list(anomaly_types))},
    )


def apply_intervention(*, decision: AutonomousSessionInterventionDecision, automatic: bool = True) -> AutonomousSessionInterventionRecord | None:
    session = decision.linked_session
    if automatic and not decision.auto_applicable:
        decision.decision_status = AutonomousSessionInterventionDecisionStatus.SKIPPED
        decision.save(update_fields=['decision_status', 'updated_at'])
        return AutonomousSessionInterventionRecord.objects.create(
            linked_session=session,
            linked_intervention_decision=decision,
            intervention_status=AutonomousSessionInterventionStatus.SKIPPED,
            intervention_summary='Automatic apply skipped because decision is not marked auto-applicable.',
            metadata={'automatic': True},
        )

    try:
        if decision.decision_type == AutonomousSessionInterventionDecisionType.PAUSE_SESSION:
            pause_autonomous_session(session, reason_codes=['health_intervention_pause'])
            status = AutonomousSessionInterventionStatus.APPLIED
            summary = 'Session paused by health intervention.'
        elif decision.decision_type == AutonomousSessionInterventionDecisionType.STOP_SESSION:
            stop_autonomous_session(session, reason_codes=['health_intervention_stop'])
            status = AutonomousSessionInterventionStatus.APPLIED
            summary = 'Session stopped by health intervention.'
        elif decision.decision_type == AutonomousSessionInterventionDecisionType.RESUME_SESSION:
            resume_autonomous_session(session)
            status = AutonomousSessionInterventionStatus.APPLIED
            summary = 'Session resumed by health intervention.'
        elif decision.decision_type == AutonomousSessionInterventionDecisionType.ESCALATE_TO_INCIDENT_REVIEW:
            status = AutonomousSessionInterventionStatus.BLOCKED
            summary = 'Escalation requires incident commander/operator review.'
        elif decision.decision_type == AutonomousSessionInterventionDecisionType.REQUIRE_MANUAL_REVIEW:
            status = AutonomousSessionInterventionStatus.BLOCKED
            summary = 'Manual review required before applying changes.'
        else:
            status = AutonomousSessionInterventionStatus.SKIPPED
            summary = 'No intervention needed; keep running.'

        decision.decision_status = (
            AutonomousSessionInterventionDecisionStatus.APPLIED
            if status == AutonomousSessionInterventionStatus.APPLIED
            else AutonomousSessionInterventionDecisionStatus.BLOCKED
            if status == AutonomousSessionInterventionStatus.BLOCKED
            else AutonomousSessionInterventionDecisionStatus.SKIPPED
        )
        decision.save(update_fields=['decision_status', 'updated_at'])
        return AutonomousSessionInterventionRecord.objects.create(
            linked_session=session,
            linked_intervention_decision=decision,
            intervention_status=status,
            intervention_summary=summary,
            metadata={'automatic': automatic},
        )
    except Exception as exc:  # pragma: no cover
        decision.decision_status = AutonomousSessionInterventionDecisionStatus.BLOCKED
        decision.save(update_fields=['decision_status', 'updated_at'])
        return AutonomousSessionInterventionRecord.objects.create(
            linked_session=session,
            linked_intervention_decision=decision,
            intervention_status=AutonomousSessionInterventionStatus.FAILED,
            intervention_summary='Intervention failed during apply.',
            metadata={'error': str(exc), 'automatic': automatic},
        )
