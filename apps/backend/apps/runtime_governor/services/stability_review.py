from __future__ import annotations

from apps.runtime_governor.models import (
    RuntimeModeStabilityReview,
    RuntimeModeStabilityReviewSeverity,
    RuntimeModeStabilityReviewType,
    RuntimeModeTransitionSnapshot,
)

MIN_DWELL_SECONDS = 600
RELAXATION_DWELL_SECONDS = 1800

CONSERVATIVE_LEVELS = {
    'BALANCED': 0,
    'CAUTION': 1,
    'MONITOR_ONLY': 2,
    'THROTTLED': 3,
    'RECOVERY_MODE': 4,
    'BLOCKED': 5,
}


def _is_relaxation(snapshot: RuntimeModeTransitionSnapshot) -> bool:
    return CONSERVATIVE_LEVELS.get(snapshot.target_mode, 0) < CONSERVATIVE_LEVELS.get(snapshot.current_mode, 0)


def build_runtime_mode_stability_review(*, transition_snapshot: RuntimeModeTransitionSnapshot) -> RuntimeModeStabilityReview:
    reason_codes = list(transition_snapshot.reason_codes or [])
    is_relaxation = bool((transition_snapshot.metadata or {}).get('is_relaxation')) or _is_relaxation(transition_snapshot)

    review_type = RuntimeModeStabilityReviewType.STABLE_TRANSITION
    severity = RuntimeModeStabilityReviewSeverity.INFO
    review_summary = 'Transition appears stable for current dwell and switch cadence.'

    if transition_snapshot.recent_switch_count >= 3:
        review_type = RuntimeModeStabilityReviewType.FLAPPING_RISK
        severity = RuntimeModeStabilityReviewSeverity.CRITICAL
        reason_codes.append('flapping_risk')
        review_summary = 'Frequent recent global mode switches indicate high flapping risk.'
    elif transition_snapshot.target_mode in {'RECOVERY_MODE', 'BLOCKED'} and transition_snapshot.target_mode != transition_snapshot.current_mode:
        review_type = RuntimeModeStabilityReviewType.SAFE_RECOVERY_ENTRY
        severity = RuntimeModeStabilityReviewSeverity.INFO
        reason_codes.append('safe_recovery_entry')
        review_summary = 'Escalation into protective mode is considered safe to allow quickly.'
    elif is_relaxation and transition_snapshot.time_in_current_mode_seconds < RELAXATION_DWELL_SECONDS:
        review_type = RuntimeModeStabilityReviewType.EARLY_RELAX_ATTEMPT
        severity = RuntimeModeStabilityReviewSeverity.HIGH
        reason_codes.append('early_relaxation')
        review_summary = 'Relaxation attempt is premature relative to recovery/throttled dwell policy.'
    elif transition_snapshot.time_in_current_mode_seconds < MIN_DWELL_SECONDS:
        review_type = RuntimeModeStabilityReviewType.INSUFFICIENT_DWELL_TIME
        severity = RuntimeModeStabilityReviewSeverity.CAUTION
        reason_codes.append('insufficient_dwell_time')
        review_summary = 'Current mode has not met minimum dwell time yet.'
    elif is_relaxation:
        review_type = RuntimeModeStabilityReviewType.SAFE_RELAXATION_WINDOW
        severity = RuntimeModeStabilityReviewSeverity.INFO
        reason_codes.append('safe_relaxation_window')
        review_summary = 'Relaxation window satisfies dwell requirements.'

    return RuntimeModeStabilityReview.objects.create(
        linked_transition_snapshot=transition_snapshot,
        review_type=review_type,
        review_severity=severity,
        review_summary=review_summary,
        reason_codes=list(dict.fromkeys(reason_codes)),
        metadata={
            'min_dwell_seconds': MIN_DWELL_SECONDS,
            'relaxation_dwell_seconds': RELAXATION_DWELL_SECONDS,
            'is_relaxation': is_relaxation,
        },
    )
