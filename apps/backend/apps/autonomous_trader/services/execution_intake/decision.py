from __future__ import annotations

from decimal import Decimal

from apps.autonomous_trader.models import (
    AutonomousExecutionDecision,
    AutonomousExecutionDecisionStatus,
    AutonomousExecutionDecisionType,
    AutonomousExecutionIntakeCandidate,
    AutonomousExecutionIntakeStatus,
)
from apps.runtime_governor.mode_enforcement.services.enforcement import get_module_enforcement_state


def decide_intake_candidate(*, candidate: AutonomousExecutionIntakeCandidate) -> AutonomousExecutionDecision:
    reason_codes = list(candidate.reason_codes or [])
    enforcement = get_module_enforcement_state(module_name='execution_intake')
    intake_impact = (enforcement.get('impact') or {}).get('impact_status')
    metadata = {'approval_status': candidate.approval_status, 'mode_enforcement': enforcement}

    if intake_impact in {'MONITOR_ONLY', 'BLOCKED'}:
        return AutonomousExecutionDecision.objects.create(
            linked_intake_candidate=candidate,
            decision_type=AutonomousExecutionDecisionType.BLOCK,
            decision_status=AutonomousExecutionDecisionStatus.BLOCKED,
            decision_confidence=Decimal('0.9950'),
            rationale='Global mode enforcement blocked new autonomous execution intake.',
            reason_codes=reason_codes + ['GLOBAL_MODE_ENFORCEMENT_BLOCKED'],
            metadata=metadata,
        )

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

    if intake_impact in {'REDUCED', 'THROTTLED'}:
        return AutonomousExecutionDecision.objects.create(
            linked_intake_candidate=candidate,
            decision_type=AutonomousExecutionDecisionType.EXECUTE_REDUCED,
            decision_status=AutonomousExecutionDecisionStatus.PROPOSED,
            decision_confidence=candidate.readiness_confidence,
            rationale='Global mode enforcement reduced execution intake to conservative reduced dispatch.',
            reason_codes=reason_codes + ['GLOBAL_MODE_ENFORCEMENT_REDUCED'],
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
