from dataclasses import dataclass

from apps.opportunity_supervisor.models import OpportunityExecutionPath
from apps.policy_engine.models import ApprovalDecisionType
from apps.runtime_governor.services import get_capabilities_for_current_mode


@dataclass
class ExecutionPathDecision:
    path: str
    queue_required: bool
    auto_execute_allowed: bool
    explanation: str


def resolve_execution_path(*, policy_decision: str, runtime_mode: str, safety_status: str, blocked_reasons: list[str], risk_level: str, has_allocation: bool, portfolio_throttle_state: str | None = None, portfolio_size_multiplier: str | float | None = None) -> ExecutionPathDecision:
    runtime_caps = get_capabilities_for_current_mode()

    if portfolio_throttle_state == 'BLOCK_NEW_ENTRIES':
        return ExecutionPathDecision(
            path=OpportunityExecutionPath.BLOCKED,
            queue_required=False,
            auto_execute_allowed=False,
            explanation='Portfolio governor blocked new entries for this cycle.',
        )

    if blocked_reasons or safety_status in {'KILL_SWITCH', 'HARD_STOP', 'PAUSED'}:
        reason = '; '.join(blocked_reasons) if blocked_reasons else f'Safety status {safety_status} blocks progression.'
        return ExecutionPathDecision(path=OpportunityExecutionPath.BLOCKED, queue_required=False, auto_execute_allowed=False, explanation=reason)

    if not has_allocation:
        return ExecutionPathDecision(
            path=OpportunityExecutionPath.WATCH,
            queue_required=False,
            auto_execute_allowed=False,
            explanation='No allocation quantity available; keep in watch/proposal-only stage.',
        )

    if policy_decision == ApprovalDecisionType.HARD_BLOCK:
        return ExecutionPathDecision(path=OpportunityExecutionPath.BLOCKED, queue_required=False, auto_execute_allowed=False, explanation='Policy hard block.')

    if portfolio_throttle_state == 'THROTTLED' and portfolio_size_multiplier not in {None, '0', 0}:
        return ExecutionPathDecision(
            path=OpportunityExecutionPath.PROPOSAL_ONLY,
            queue_required=False,
            auto_execute_allowed=False,
            explanation='Portfolio governor throttled entries; keep as proposal-only for conservative flow.',
        )

    if (not runtime_caps['allow_auto_execution']) or runtime_caps['require_operator_for_all_trades']:
        return ExecutionPathDecision(
            path=OpportunityExecutionPath.QUEUE,
            queue_required=True,
            auto_execute_allowed=False,
            explanation=f'Runtime mode {runtime_mode} requires operator queue for execution.',
        )

    if policy_decision == ApprovalDecisionType.APPROVAL_REQUIRED or risk_level == 'HIGH':
        return ExecutionPathDecision(
            path=OpportunityExecutionPath.QUEUE,
            queue_required=True,
            auto_execute_allowed=False,
            explanation='Policy/risk requires manual operator approval.',
        )

    if policy_decision == ApprovalDecisionType.AUTO_APPROVE and runtime_caps['allow_auto_execution']:
        return ExecutionPathDecision(
            path=OpportunityExecutionPath.AUTO_EXECUTE_PAPER,
            queue_required=False,
            auto_execute_allowed=True,
            explanation='Runtime and policy allow paper auto-execution.',
        )

    return ExecutionPathDecision(
        path=OpportunityExecutionPath.PROPOSAL_ONLY,
        queue_required=False,
        auto_execute_allowed=False,
        explanation='Proposal generated but execution is not auto-authorized.',
    )
