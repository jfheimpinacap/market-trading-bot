from __future__ import annotations

from dataclasses import dataclass

from apps.mission_control.models import (
    AutonomousCadenceDecision,
    AutonomousProfileActivityState,
    AutonomousProfileContextStatus,
    AutonomousProfilePortfolioPressureState,
    AutonomousProfileRuntimePosture,
    AutonomousProfileSafetyPosture,
    AutonomousRecentLossState,
    AutonomousRuntimeSession,
    AutonomousSessionContextReview,
    AutonomousSessionTimingSnapshot,
)
from apps.runtime_governor.services import get_capabilities_for_current_mode
from apps.safety_guard.services import get_safety_status


@dataclass
class ContextReviewResult:
    review: AutonomousSessionContextReview
    reason_codes: list[str]


def _map_portfolio_pressure(value: str) -> str:
    normalized = (value or '').upper()
    if normalized in {
        AutonomousProfilePortfolioPressureState.CAUTION,
        AutonomousProfilePortfolioPressureState.THROTTLED,
        AutonomousProfilePortfolioPressureState.BLOCK_NEW_ENTRIES,
    }:
        return normalized
    if 'BLOCK' in normalized:
        return AutonomousProfilePortfolioPressureState.BLOCK_NEW_ENTRIES
    if 'THROTTLE' in normalized:
        return AutonomousProfilePortfolioPressureState.THROTTLED
    if 'CAUTION' in normalized or 'ELEVATED' in normalized:
        return AutonomousProfilePortfolioPressureState.CAUTION
    return AutonomousProfilePortfolioPressureState.NORMAL


def build_session_context_review(*, session: AutonomousRuntimeSession, selection_run=None) -> ContextReviewResult:
    latest_snapshot = session.timing_snapshots.select_related('linked_schedule_profile').order_by('-created_at', '-id').first()
    latest_cadence = session.cadence_decisions.order_by('-created_at', '-id').first()

    reason_codes: list[str] = []
    portfolio_state = _map_portfolio_pressure((latest_cadence.portfolio_posture if latest_cadence else '') or 'NORMAL')
    runtime_state = AutonomousProfileRuntimePosture.NORMAL
    safety_state = AutonomousProfileSafetyPosture.NORMAL

    capabilities = get_capabilities_for_current_mode()
    if not bool(capabilities.get('allow_signal_generation', False) and capabilities.get('allow_proposals', False)):
        runtime_state = AutonomousProfileRuntimePosture.BLOCKED
        reason_codes.append('runtime_capability_block')
    elif latest_cadence and 'CAUTION' in (latest_cadence.runtime_posture or '').upper():
        runtime_state = AutonomousProfileRuntimePosture.CAUTION
        reason_codes.append('runtime_caution_posture')

    safety = get_safety_status()
    if safety.get('kill_switch_enabled') or safety.get('hard_stop_active'):
        safety_state = AutonomousProfileSafetyPosture.HARD_BLOCK
        reason_codes.append('safety_hard_block')
    elif latest_cadence and 'CAUTION' in (latest_cadence.safety_posture or '').upper():
        safety_state = AutonomousProfileSafetyPosture.CAUTION
        reason_codes.append('safety_caution_posture')

    if portfolio_state != AutonomousProfilePortfolioPressureState.NORMAL:
        reason_codes.append(f'portfolio_{portfolio_state.lower()}')

    signal_state = latest_snapshot.signal_pressure_state if latest_snapshot else 'NORMAL'
    if signal_state in {'LOW', 'QUIET'}:
        reason_codes.append(f'signal_{signal_state.lower()}')

    recent_loss_count = latest_snapshot.recent_loss_count if latest_snapshot else 0
    if recent_loss_count >= 2:
        recent_loss_state = AutonomousRecentLossState.REPEATED_LOSS
    elif recent_loss_count == 1:
        recent_loss_state = AutonomousRecentLossState.RECENT_LOSS
    else:
        recent_loss_state = AutonomousRecentLossState.NONE

    if recent_loss_state != AutonomousRecentLossState.NONE:
        reason_codes.append(recent_loss_state.lower())

    no_action_ticks = latest_snapshot.consecutive_no_action_ticks if latest_snapshot else 0
    blocked_ticks = latest_snapshot.consecutive_blocked_ticks if latest_snapshot else 0
    recent_dispatch_count = latest_snapshot.recent_dispatch_count if latest_snapshot else 0

    if blocked_ticks >= 2:
        activity_state = AutonomousProfileActivityState.REPEATED_BLOCKED
        reason_codes.append('repeated_blocked_ticks')
    elif no_action_ticks >= 4:
        activity_state = AutonomousProfileActivityState.REPEATED_NO_ACTION
        reason_codes.append('repeated_no_action_ticks')
    elif recent_dispatch_count == 0:
        activity_state = AutonomousProfileActivityState.LOW_ACTIVITY
        reason_codes.append('low_activity')
    else:
        activity_state = AutonomousProfileActivityState.ACTIVE

    if runtime_state == AutonomousProfileRuntimePosture.BLOCKED or safety_state == AutonomousProfileSafetyPosture.HARD_BLOCK:
        context_status = AutonomousProfileContextStatus.BLOCKED
    elif (
        portfolio_state in {AutonomousProfilePortfolioPressureState.THROTTLED, AutonomousProfilePortfolioPressureState.BLOCK_NEW_ENTRIES}
        or activity_state in {AutonomousProfileActivityState.REPEATED_BLOCKED, AutonomousProfileActivityState.REPEATED_NO_ACTION}
        or signal_state in {'LOW', 'QUIET'}
        or recent_loss_state == AutonomousRecentLossState.REPEATED_LOSS
    ):
        context_status = AutonomousProfileContextStatus.NEEDS_MORE_CONSERVATIVE_PROFILE
    elif (
        portfolio_state == AutonomousProfilePortfolioPressureState.NORMAL
        and runtime_state == AutonomousProfileRuntimePosture.NORMAL
        and safety_state == AutonomousProfileSafetyPosture.NORMAL
        and signal_state in {'NORMAL', 'HIGH'}
        and activity_state in {AutonomousProfileActivityState.ACTIVE, AutonomousProfileActivityState.LOW_ACTIVITY}
        and recent_loss_state == AutonomousRecentLossState.NONE
    ):
        context_status = AutonomousProfileContextStatus.NEEDS_MORE_ACTIVE_PROFILE
    else:
        context_status = AutonomousProfileContextStatus.HOLD_CURRENT

    if context_status == AutonomousProfileContextStatus.NEEDS_MORE_ACTIVE_PROFILE and (
        session.linked_schedule_profile and session.linked_schedule_profile.slug == 'balanced_local'
    ):
        context_status = AutonomousProfileContextStatus.STABLE

    review = AutonomousSessionContextReview.objects.create(
        linked_selection_run=selection_run,
        linked_session=session,
        linked_current_profile=session.linked_schedule_profile,
        linked_latest_timing_snapshot=latest_snapshot,
        portfolio_pressure_state=portfolio_state,
        runtime_posture=runtime_state,
        safety_posture=safety_state,
        signal_pressure_state=signal_state,
        recent_loss_state=recent_loss_state,
        activity_state=activity_state,
        context_status=context_status,
        context_summary=(
            f'context={context_status} portfolio={portfolio_state} runtime={runtime_state} '
            f'safety={safety_state} signal={signal_state} activity={activity_state}'
        ),
        reason_codes=list(dict.fromkeys(reason_codes)),
        metadata={
            'latest_snapshot_id': latest_snapshot.id if latest_snapshot else None,
            'latest_cadence_decision_id': latest_cadence.id if latest_cadence else None,
        },
    )
    return ContextReviewResult(review=review, reason_codes=review.reason_codes or [])
