from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Any

from apps.runtime_governor.services.stability_review import MIN_DWELL_SECONDS, RELAXATION_DWELL_SECONDS
from apps.runtime_governor.tuning_profiles import get_runtime_conservative_tuning_profile


def _fingerprint(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()[:16]


def build_runtime_tuning_context(*, summary_scope: str) -> dict[str, Any]:
    tuning = get_runtime_conservative_tuning_profile()
    effective_values = {
        'high_backlog_manual_review_bias': tuning.high_backlog_manual_review_bias,
        'critical_backlog_monitor_only_bias': tuning.critical_backlog_monitor_only_bias,
        'critical_backlog_blocks_relax': tuning.critical_backlog_blocks_relax,
        'high_backlog_relax_dwell_multiplier': tuning.high_backlog_relax_dwell_multiplier,
        'critical_backlog_relax_dwell_multiplier': tuning.critical_backlog_relax_dwell_multiplier,
    }
    guardrails_by_scope: dict[str, dict[str, Any]] = {
        'runtime_feedback_summary': {
            'high_backlog_manual_review_bias': tuning.high_backlog_manual_review_bias,
            'critical_backlog_monitor_only_bias': tuning.critical_backlog_monitor_only_bias,
            'critical_backlog_blocks_relax': tuning.critical_backlog_blocks_relax,
            'high_backlog_behavior': 'defer_relaxation_and_reduce_admission_cadence',
            'critical_backlog_behavior': 'monitor_only_or_manual_review_bias',
        },
        'operating_mode_summary': {
            'high_backlog_target_bias': 'THROTTLED',
            'high_backlog_manual_review_bias': tuning.high_backlog_manual_review_bias,
            'critical_backlog_target_bias': 'MONITOR_ONLY',
            'critical_backlog_monitor_only_bias': tuning.critical_backlog_monitor_only_bias,
            'critical_backlog_blocks_relax': tuning.critical_backlog_blocks_relax,
        },
        'mode_stabilization_summary': {
            'min_dwell_seconds': MIN_DWELL_SECONDS,
            'base_relaxation_dwell_seconds': RELAXATION_DWELL_SECONDS,
            'high_backlog_relax_dwell_multiplier': tuning.high_backlog_relax_dwell_multiplier,
            'critical_backlog_relax_dwell_multiplier': tuning.critical_backlog_relax_dwell_multiplier,
            'critical_backlog_blocks_relax': tuning.critical_backlog_blocks_relax,
        },
        'mode_enforcement_summary': {
            'derived_from_global_operating_mode': True,
            'upstream_high_backlog_target_bias': 'THROTTLED',
            'upstream_critical_backlog_target_bias': 'MONITOR_ONLY',
            'upstream_high_backlog_manual_review_bias': tuning.high_backlog_manual_review_bias,
            'upstream_critical_backlog_monitor_only_bias': tuning.critical_backlog_monitor_only_bias,
        },
    }
    tuning_values = asdict(tuning)
    fingerprint_seed = {
        'summary_scope': summary_scope,
        'profile_name': tuning.profile_name,
        'tuning_values': tuning_values,
        'guardrails': guardrails_by_scope.get(summary_scope, {}),
    }
    return {
        'tuning_profile_name': tuning.profile_name,
        'tuning_profile_summary': (
            'Active conservative runtime tuning profile propagated into this operational summary '
            'for traceability only. No decision logic is changed by this response field.'
        ),
        'tuning_profile_fingerprint': _fingerprint(fingerprint_seed),
        'tuning_effective_values': effective_values,
        'tuning_guardrail_summary': guardrails_by_scope.get(summary_scope, {}),
    }

