from __future__ import annotations

from dataclasses import asdict

from apps.runtime_governor.services.stability_review import MIN_DWELL_SECONDS, RELAXATION_DWELL_SECONDS
from apps.runtime_governor.tuning_profiles import get_runtime_conservative_tuning_profile


def build_runtime_tuning_profile_snapshot() -> dict:
    tuning = get_runtime_conservative_tuning_profile()
    backlog_thresholds = {
        'caution': tuning.backlog_caution_threshold,
        'high': tuning.backlog_high_threshold,
        'critical': tuning.backlog_critical_threshold,
    }
    backlog_weights = {
        'overdue_weight': tuning.overdue_weight,
        'stale_blocked_weight': tuning.stale_blocked_weight,
        'followup_due_weight': tuning.followup_due_weight,
        'overdue_p1_weight': tuning.overdue_p1_weight,
        'persistent_stale_blocked_weight': tuning.persistent_stale_blocked_weight,
    }
    feedback_guardrails = {
        'high_backlog_manual_review_bias': tuning.high_backlog_manual_review_bias,
        'critical_backlog_monitor_only_bias': tuning.critical_backlog_monitor_only_bias,
        'critical_backlog_blocks_relax': tuning.critical_backlog_blocks_relax,
        'runtime_feedback_high_backlog_relaxation_behavior': 'defer_relaxation_and_reduce_admission_cadence',
        'runtime_feedback_critical_backlog_behavior': 'monitor_only_or_manual_review_bias',
    }
    operating_mode_guardrails = {
        'high_backlog_target_bias': 'THROTTLED',
        'high_backlog_manual_review_bias': tuning.high_backlog_manual_review_bias,
        'critical_backlog_target_bias': 'MONITOR_ONLY',
        'critical_backlog_monitor_only_bias': tuning.critical_backlog_monitor_only_bias,
        'critical_backlog_blocks_relax': tuning.critical_backlog_blocks_relax,
    }
    stabilization_guardrails = {
        'min_dwell_seconds': MIN_DWELL_SECONDS,
        'base_relaxation_dwell_seconds': RELAXATION_DWELL_SECONDS,
        'high_backlog_relax_dwell_multiplier': tuning.high_backlog_relax_dwell_multiplier,
        'critical_backlog_relax_dwell_multiplier': tuning.critical_backlog_relax_dwell_multiplier,
        'critical_backlog_blocks_relax': tuning.critical_backlog_blocks_relax,
    }
    effective_values = {
        'high_backlog_manual_review_bias': tuning.high_backlog_manual_review_bias,
        'critical_backlog_monitor_only_bias': tuning.critical_backlog_monitor_only_bias,
        'critical_backlog_blocks_relax': tuning.critical_backlog_blocks_relax,
        'high_backlog_relax_dwell_multiplier': tuning.high_backlog_relax_dwell_multiplier,
        'critical_backlog_relax_dwell_multiplier': tuning.critical_backlog_relax_dwell_multiplier,
    }
    summary = (
        'Read-only runtime governor tuning snapshot. Shows the active conservative profile, '
        'backlog pressure thresholds/weights, and guardrails used by runtime feedback, '
        'operating mode, and stabilization. This endpoint does not modify runtime behavior.'
    )
    return {
        'profile_name': tuning.profile_name,
        'backlog_thresholds': backlog_thresholds,
        'backlog_weights': backlog_weights,
        'feedback_guardrails': feedback_guardrails,
        'operating_mode_guardrails': operating_mode_guardrails,
        'stabilization_guardrails': stabilization_guardrails,
        'effective_values': effective_values,
        'summary': summary,
        'created_at': None,
        'profile_values': asdict(tuning),
    }
