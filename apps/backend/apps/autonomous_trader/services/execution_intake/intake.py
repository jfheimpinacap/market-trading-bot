from __future__ import annotations

from dataclasses import dataclass

from apps.autonomous_trader.models import AutonomousExecutionIntakeCandidate, AutonomousExecutionIntakeStatus
from apps.risk_agent.models import AutonomousExecutionReadiness


@dataclass
class IntakeBuildResult:
    candidates: list[AutonomousExecutionIntakeCandidate]


def build_intake_candidates(*, run, limit: int = 25) -> IntakeBuildResult:
    readiness_rows = AutonomousExecutionReadiness.objects.select_related(
        'linked_market',
        'linked_approval_review',
        'linked_sizing_plan',
        'linked_watch_plan',
        'linked_approval_review__linked_candidate',
    ).order_by('-created_at', '-id')[:limit]

    created: list[AutonomousExecutionIntakeCandidate] = []
    for readiness in readiness_rows:
        approval = readiness.linked_approval_review
        approval_status = approval.approval_status if approval else ''
        status = AutonomousExecutionIntakeStatus.INSUFFICIENT_CONTEXT
        reason_codes = list(readiness.readiness_reason_codes or [])

        if readiness.readiness_status == 'READY':
            status = AutonomousExecutionIntakeStatus.READY_FOR_AUTONOMOUS_EXECUTION
        elif readiness.readiness_status == 'READY_REDUCED':
            status = AutonomousExecutionIntakeStatus.READY_REDUCED
        elif readiness.readiness_status == 'WATCH_ONLY':
            status = AutonomousExecutionIntakeStatus.WATCH_ONLY
        elif readiness.readiness_status == 'DEFERRED':
            status = AutonomousExecutionIntakeStatus.DEFERRED
        elif readiness.readiness_status == 'BLOCKED':
            status = AutonomousExecutionIntakeStatus.BLOCKED

        if approval_status == 'BLOCKED':
            status = AutonomousExecutionIntakeStatus.BLOCKED
            reason_codes.append('APPROVAL_BLOCKED')

        if approval_status == 'NEEDS_REVIEW' and status in {
            AutonomousExecutionIntakeStatus.READY_FOR_AUTONOMOUS_EXECUTION,
            AutonomousExecutionIntakeStatus.READY_REDUCED,
        }:
            status = AutonomousExecutionIntakeStatus.INSUFFICIENT_CONTEXT
            reason_codes.append('APPROVAL_NEEDS_REVIEW')

        created.append(
            AutonomousExecutionIntakeCandidate.objects.create(
                intake_run=run,
                linked_market=readiness.linked_market,
                linked_execution_readiness=readiness,
                linked_approval_review=approval,
                linked_sizing_plan=readiness.linked_sizing_plan,
                linked_watch_plan=readiness.linked_watch_plan,
                linked_prediction_context=(approval.linked_candidate.metadata or {}) if approval else {},
                linked_portfolio_context=(approval.linked_candidate.linked_portfolio_context or {}) if approval else {},
                intake_status=status,
                readiness_confidence=readiness.readiness_confidence,
                approval_status=approval_status,
                sizing_method=readiness.linked_sizing_plan.sizing_mode if readiness.linked_sizing_plan else '',
                execution_context_summary=readiness.readiness_summary,
                reason_codes=reason_codes,
                metadata={
                    'readiness_status': readiness.readiness_status,
                    'readiness_id': readiness.id,
                },
            )
        )

    return IntakeBuildResult(candidates=created)
