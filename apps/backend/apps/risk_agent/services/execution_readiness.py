from __future__ import annotations

from decimal import Decimal

from apps.risk_agent.models import (
    AutonomousExecutionReadiness,
    AutonomousExecutionReadinessStatus,
    PositionWatchPlan,
    RiskApprovalDecision,
    RiskRuntimeApprovalStatus,
    RiskSizingPlan,
)


def build_execution_readiness(*, approval_decision: RiskApprovalDecision, sizing_plan: RiskSizingPlan, watch_plan: PositionWatchPlan) -> AutonomousExecutionReadiness:
    status = AutonomousExecutionReadinessStatus.DEFERRED
    reason_codes = list(approval_decision.reason_codes or [])

    if approval_decision.approval_status == RiskRuntimeApprovalStatus.APPROVED:
        status = AutonomousExecutionReadinessStatus.READY
        reason_codes.append('APPROVAL_READY')
    elif approval_decision.approval_status == RiskRuntimeApprovalStatus.APPROVED_REDUCED:
        status = AutonomousExecutionReadinessStatus.READY_REDUCED
        reason_codes.append('APPROVAL_REDUCED')
    elif approval_decision.approval_status == RiskRuntimeApprovalStatus.BLOCKED:
        status = AutonomousExecutionReadinessStatus.BLOCKED
        reason_codes.append('APPROVAL_BLOCKED')
    elif approval_decision.approval_status == RiskRuntimeApprovalStatus.NEEDS_REVIEW:
        status = AutonomousExecutionReadinessStatus.DEFERRED
        reason_codes.append('REQUIRES_MANUAL_REVIEW')

    if watch_plan.watch_status == 'REQUIRED' and status == AutonomousExecutionReadinessStatus.DEFERRED:
        status = AutonomousExecutionReadinessStatus.WATCH_ONLY

    confidence = Decimal(str(approval_decision.approval_confidence or '0'))
    if status == AutonomousExecutionReadinessStatus.READY_REDUCED:
        confidence *= Decimal('0.90')

    return AutonomousExecutionReadiness.objects.create(
        linked_market=approval_decision.linked_candidate.linked_market,
        linked_approval_review=approval_decision,
        linked_sizing_plan=sizing_plan,
        linked_watch_plan=watch_plan,
        readiness_status=status,
        readiness_confidence=max(Decimal('0.0000'), min(Decimal('1.0000'), confidence)),
        readiness_summary=(
            f'Autonomous readiness={status} from approval={approval_decision.approval_status}, '
            f'sizing={sizing_plan.sizing_mode}, watch={watch_plan.watch_status}.'
        ),
        readiness_reason_codes=reason_codes,
        metadata={
            'paper_only': True,
            'autonomous_trader_handoff': status in {AutonomousExecutionReadinessStatus.READY, AutonomousExecutionReadinessStatus.READY_REDUCED},
            'execution_authority': 'autonomous_trader',
        },
    )
