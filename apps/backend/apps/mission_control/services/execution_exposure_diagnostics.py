from __future__ import annotations

from typing import Any


EXECUTION_EXPOSURE_PROVENANCE_UNAVAILABLE = 'EXECUTION_EXPOSURE_PROVENANCE_UNAVAILABLE'
EXECUTION_EXPOSURE_RELEASE_AUDIT_UNAVAILABLE = 'EXECUTION_EXPOSURE_RELEASE_AUDIT_UNAVAILABLE'
TEST_CONSOLE_EXPOSURE_DIAGNOSTIC_FALLBACK_USED = 'TEST_CONSOLE_EXPOSURE_DIAGNOSTIC_FALLBACK_USED'
TEST_CONSOLE_EXPORT_PARTIAL_DIAGNOSTIC_RECOVERED = 'TEST_CONSOLE_EXPORT_PARTIAL_DIAGNOSTIC_RECOVERED'


def empty_execution_exposure_provenance_summary(
    *,
    reason_code: str = EXECUTION_EXPOSURE_PROVENANCE_UNAVAILABLE,
    diagnostic_status: str = 'UNAVAILABLE',
) -> dict[str, Any]:
    return {
        'diagnostic_status': diagnostic_status,
        'diagnostic_unavailable': diagnostic_status != 'AVAILABLE',
        'diagnostic_reason_codes': [reason_code] if reason_code else [],
        'suppressions_total': 0,
        'suppressions_by_source_type': {},
        'suppressions_by_scope': {},
        'exact_match_count': 0,
        'weak_match_count': 0,
        'stale_exposure_suspected_count': 0,
        'additive_entries_suppressed': 0,
        'reduce_or_exit_allowed': 0,
        'dominant_exposure_reason_codes': [],
        'provenance_summary': 'UNAVAILABLE' if diagnostic_status != 'AVAILABLE' else 'AVAILABLE',
    }


def empty_execution_exposure_release_audit_summary(
    *,
    reason_code: str = EXECUTION_EXPOSURE_RELEASE_AUDIT_UNAVAILABLE,
    diagnostic_status: str = 'UNAVAILABLE',
) -> dict[str, Any]:
    return {
        'diagnostic_status': diagnostic_status,
        'diagnostic_unavailable': diagnostic_status != 'AVAILABLE',
        'diagnostic_reason_codes': [reason_code] if reason_code else [],
        'suppressions_audited': 0,
        'valid_blockers_count': 0,
        'stale_suspected_count': 0,
        'terminal_but_still_matching_count': 0,
        'session_scope_mismatch_count': 0,
        'mirror_lag_suspected_count': 0,
        'release_eligible_count': 0,
        'release_pending_confirmation_count': 0,
        'manual_review_required_count': 0,
        'keep_blocked_count': 0,
        'validity_reason_codes': [],
        'release_reason_codes': [],
        'release_audit_summary': 'UNAVAILABLE' if diagnostic_status != 'AVAILABLE' else 'AVAILABLE',
    }


def normalize_execution_exposure_diagnostics(
    *,
    provenance_summary: Any,
    provenance_examples: Any,
    release_audit_summary: Any,
    release_audit_examples: Any,
) -> dict[str, Any]:
    fallback_reason_codes: list[str] = []

    if isinstance(provenance_summary, dict):
        normalized_provenance_summary = dict(provenance_summary)
        normalized_provenance_summary.setdefault('diagnostic_status', 'AVAILABLE')
        normalized_provenance_summary.setdefault('diagnostic_unavailable', False)
        normalized_provenance_summary.setdefault('diagnostic_reason_codes', [])
    else:
        normalized_provenance_summary = empty_execution_exposure_provenance_summary()
        fallback_reason_codes.append(EXECUTION_EXPOSURE_PROVENANCE_UNAVAILABLE)

    normalized_provenance_examples = list(provenance_examples) if isinstance(provenance_examples, list) else []
    if not isinstance(provenance_examples, list):
        fallback_reason_codes.append(EXECUTION_EXPOSURE_PROVENANCE_UNAVAILABLE)

    if isinstance(release_audit_summary, dict):
        normalized_release_audit_summary = dict(release_audit_summary)
        normalized_release_audit_summary.setdefault('diagnostic_status', 'AVAILABLE')
        normalized_release_audit_summary.setdefault('diagnostic_unavailable', False)
        normalized_release_audit_summary.setdefault('diagnostic_reason_codes', [])
    else:
        normalized_release_audit_summary = empty_execution_exposure_release_audit_summary()
        fallback_reason_codes.append(EXECUTION_EXPOSURE_RELEASE_AUDIT_UNAVAILABLE)

    normalized_release_audit_examples = list(release_audit_examples) if isinstance(release_audit_examples, list) else []
    if not isinstance(release_audit_examples, list):
        fallback_reason_codes.append(EXECUTION_EXPOSURE_RELEASE_AUDIT_UNAVAILABLE)

    fallback_used = bool(fallback_reason_codes)
    if fallback_used:
        normalized_provenance_summary.setdefault('diagnostic_status', 'DEGRADED')
        normalized_provenance_summary['diagnostic_unavailable'] = True
        normalized_release_audit_summary.setdefault('diagnostic_status', 'DEGRADED')
        normalized_release_audit_summary['diagnostic_unavailable'] = True

    return {
        'execution_exposure_provenance_summary': normalized_provenance_summary,
        'execution_exposure_provenance_examples': normalized_provenance_examples,
        'execution_exposure_release_audit_summary': normalized_release_audit_summary,
        'execution_exposure_release_audit_examples': normalized_release_audit_examples,
        'fallback_used': fallback_used,
        'fallback_reason_codes': list(dict.fromkeys(fallback_reason_codes)),
    }
