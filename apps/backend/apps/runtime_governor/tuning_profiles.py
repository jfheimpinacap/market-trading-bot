from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConservativeTuningProfile:
    profile_name: str = 'runtime_conservative_default'
    backlog_caution_threshold: int = 6
    backlog_high_threshold: int = 16
    backlog_critical_threshold: int = 999_999
    overdue_weight: int = 2
    stale_blocked_weight: int = 1
    followup_due_weight: int = 0
    overdue_p1_weight: int = 3
    persistent_stale_blocked_weight: int = 2
    high_backlog_relax_dwell_multiplier: float = 1.5
    critical_backlog_relax_dwell_multiplier: float = 2.0
    critical_backlog_blocks_relax: bool = True
    high_backlog_manual_review_bias: bool = True
    critical_backlog_monitor_only_bias: bool = True


DEFAULT_CONSERVATIVE_TUNING_PROFILE = ConservativeTuningProfile()


def get_runtime_conservative_tuning_profile() -> ConservativeTuningProfile:
    return DEFAULT_CONSERVATIVE_TUNING_PROFILE
