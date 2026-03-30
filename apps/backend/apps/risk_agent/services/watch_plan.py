from __future__ import annotations

from apps.risk_agent.models import (
    PositionWatchPlan,
    PositionWatchPlanStatus,
    RiskApprovalDecision,
    RiskRuntimeApprovalStatus,
    RiskRuntimeCandidate,
    RiskSizingPlan,
)


def build_watch_plan(*, candidate: RiskRuntimeCandidate, sizing_plan: RiskSizingPlan, approval_decision: RiskApprovalDecision) -> PositionWatchPlan:
    watch_status = PositionWatchPlanStatus.REQUIRED
    review_interval_hint = '4h'
    escalation_path = 'risk_agent -> position_manager -> operator_queue'

    if approval_decision.approval_status == RiskRuntimeApprovalStatus.BLOCKED:
        watch_status = PositionWatchPlanStatus.NOT_NEEDED
        review_interval_hint = 'on_new_prediction'
        escalation_path = 'risk_agent -> prediction_agent (re-evaluate)'
    elif approval_decision.approval_status == RiskRuntimeApprovalStatus.APPROVED_REDUCED:
        review_interval_hint = '2h'

    triggers = {
        'confidence_decay': {'threshold': 0.10, 'action': 'reduce_or_exit'},
        'narrative_reversal': {'required': True, 'action': 'manual_review'},
        'market_move_against': {'threshold_bps': 900, 'action': 'review_position'},
        'time_decay': {'hours_before_close': 6, 'action': 'tighten_watch'},
        'volatility_jump': {'spread_bps': 400, 'action': 'halt_new_entries'},
    }

    return PositionWatchPlan.objects.create(
        linked_candidate=candidate,
        linked_sizing_plan=sizing_plan,
        watch_status=watch_status,
        watch_triggers=triggers,
        review_interval_hint=review_interval_hint,
        escalation_path=escalation_path,
        metadata={
            'paper_demo_only': True,
            'watch_required': approval_decision.watch_required,
            'position_manager_handoff': True,
        },
    )
