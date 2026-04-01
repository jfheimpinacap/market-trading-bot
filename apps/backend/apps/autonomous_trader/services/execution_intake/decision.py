from __future__ import annotations

from decimal import Decimal

from apps.autonomous_trader.models import (
    AutonomousExecutionDecision,
    AutonomousExecutionDecisionStatus,
    AutonomousExecutionDecisionType,
    AutonomousExecutionIntakeCandidate,
    AutonomousExecutionIntakeStatus,
)


def decide_intake_candidate(*, candidate: AutonomousExecutionIntakeCandidate) -> AutonomousExecutionDecision:
    reason_codes = list(candidate.reason_codes or [])
    metadata = {'approval_status': candidate.approval_status}

    if candidate.intake_status == AutonomousExecutionIntakeStatus.BLOCKED:
        return AutonomousExecutionDecision.objects.create(
            linked_intake_candidate=candidate,
            decision_type=AutonomousExecutionDecisionType.BLOCK,
            decision_status=AutonomousExecutionDecisionStatus.BLOCKED,
            decision_confidence=Decimal('0.9900'),
            rationale='Risk readiness or approval review blocks autonomous dispatch.',
            reason_codes=reason_codes + ['READINESS_BLOCKED'],
            metadata=metadata,
        )

    if candidate.intake_status == AutonomousExecutionIntakeStatus.DEFERRED:
        return AutonomousExecutionDecision.objects.create(
            linked_intake_candidate=candidate,
            decision_type=AutonomousExecutionDecisionType.DEFER,
            decision_status=AutonomousExecutionDecisionStatus.SKIPPED,
            decision_confidence=Decimal('0.8000'),
            rationale='Readiness status is deferred; keep out of current dispatch window.',
            reason_codes=reason_codes + ['READINESS_DEFERRED'],
            metadata=metadata,
        )

    if candidate.intake_status == AutonomousExecutionIntakeStatus.WATCH_ONLY:
        return AutonomousExecutionDecision.objects.create(
            linked_intake_candidate=candidate,
            decision_type=AutonomousExecutionDecisionType.KEEP_ON_WATCH,
            decision_status=AutonomousExecutionDecisionStatus.SKIPPED,
            decision_confidence=Decimal('0.8500'),
            rationale='Readiness indicates watch-only posture; no dispatch.',
            reason_codes=reason_codes + ['WATCH_ONLY'],
            metadata=metadata,
        )

    if candidate.intake_status == AutonomousExecutionIntakeStatus.INSUFFICIENT_CONTEXT or candidate.approval_status == 'NEEDS_REVIEW':
        return AutonomousExecutionDecision.objects.create(
            linked_intake_candidate=candidate,
            decision_type=AutonomousExecutionDecisionType.REQUIRE_MANUAL_REVIEW,
            decision_status=AutonomousExecutionDecisionStatus.BLOCKED,
            decision_confidence=Decimal('0.7000'),
            rationale='Context is not sufficient for autonomous dispatch without manual review.',
            reason_codes=reason_codes + ['INSUFFICIENT_CONTEXT'],
            metadata=metadata,
        )

    if candidate.intake_status == AutonomousExecutionIntakeStatus.READY_REDUCED:
        return AutonomousExecutionDecision.objects.create(
            linked_intake_candidate=candidate,
            decision_type=AutonomousExecutionDecisionType.EXECUTE_REDUCED,
            decision_status=AutonomousExecutionDecisionStatus.PROPOSED,
            decision_confidence=candidate.readiness_confidence,
            rationale='Readiness-approved with reduced mode for conservative paper dispatch.',
            reason_codes=reason_codes + ['READY_REDUCED'],
            metadata=metadata,
        )

    return AutonomousExecutionDecision.objects.create(
        linked_intake_candidate=candidate,
        decision_type=AutonomousExecutionDecisionType.EXECUTE_NOW,
        decision_status=AutonomousExecutionDecisionStatus.PROPOSED,
        decision_confidence=candidate.readiness_confidence,
        rationale='Readiness-approved for immediate governed paper dispatch.',
        reason_codes=reason_codes + ['READY_EXECUTE'],
        metadata=metadata,
    )
