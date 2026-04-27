from __future__ import annotations

from dataclasses import dataclass
from typing import Any


STATE_SESSION_MISMATCH = 'STATE_SESSION_MISMATCH'
STATE_WINDOW_MISMATCH = 'STATE_WINDOW_MISMATCH'
STATE_SCOPE_MISMATCH = 'STATE_SCOPE_MISMATCH'
STATE_EMPTY_FALLBACK_APPLIED = 'STATE_EMPTY_FALLBACK_APPLIED'
STATE_PORTFOLIO_ACTIVE_BUT_FUNNEL_EMPTY = 'STATE_PORTFOLIO_ACTIVE_BUT_FUNNEL_EMPTY'
STATE_GATE_BLOCKED_ON_STALE_VIEW = 'STATE_GATE_BLOCKED_ON_STALE_VIEW'
STATE_ALIGNMENT_OK = 'STATE_ALIGNMENT_OK'


@dataclass(frozen=True)
class StateConsistencySnapshot:
    summary: dict[str, Any]
    examples: list[dict[str, Any]]
    reason_codes: list[str]
    should_ignore_funnel_block: bool


def _is_portfolio_active(portfolio_summary: dict[str, Any]) -> bool:
    return bool(
        int(portfolio_summary.get('open_positions') or 0) > 0
        or int(portfolio_summary.get('recent_trades_count') or 0) > 0
    )


def _is_funnel_empty(funnel: dict[str, Any]) -> bool:
    counters = [
        int(funnel.get('scan_count') or 0),
        int(funnel.get('research_count') or 0),
        int(funnel.get('prediction_count') or 0),
        int(funnel.get('risk_decision_count') or 0),
        int(funnel.get('paper_execution_count') or 0),
    ]
    return all(value == 0 for value in counters)


def _is_current_window_empty(funnel: dict[str, Any]) -> bool:
    handoff_counters = [
        int(funnel.get('shortlisted_signals') or 0),
        int(funnel.get('handoff_candidates') or 0),
        int(funnel.get('consensus_reviews') or 0),
        int(funnel.get('prediction_candidates') or 0),
        int(funnel.get('risk_decisions') or 0),
        int(funnel.get('paper_execution_candidates') or 0),
    ]
    if any(value > 0 for value in handoff_counters):
        return False
    return _is_funnel_empty(funnel)


def _session_namespace(value: str | None) -> str | None:
    if not value:
        return None
    if ':' not in value:
        return 'generic'
    return str(value).split(':', 1)[0].strip() or 'generic'


def build_state_consistency_snapshot(
    *,
    funnel: dict[str, Any],
    portfolio_summary: dict[str, Any],
    funnel_session_detected: str | None,
    portfolio_session_detected: str | None,
    funnel_scope: str | None = None,
    portfolio_scope: str | None = None,
    stale_view_gate_blocked: bool = False,
) -> StateConsistencySnapshot:
    reason_codes: list[str] = []
    examples: list[dict[str, Any]] = []
    portfolio_active = _is_portfolio_active(portfolio_summary)
    recent_trades_count = int(portfolio_summary.get('recent_trades_count') or 0)
    funnel_empty = _is_funnel_empty(funnel)
    current_window_empty = _is_current_window_empty(funnel)

    state_window_alignment = 'ALIGNED'
    state_scope_alignment = 'ALIGNED'
    session_alignment = 'ALIGNED'

    funnel_namespace = _session_namespace(funnel_session_detected)
    portfolio_namespace = _session_namespace(portfolio_session_detected)
    if (
        funnel_session_detected
        and portfolio_session_detected
        and funnel_namespace == portfolio_namespace
        and funnel_session_detected != portfolio_session_detected
    ):
        session_alignment = 'MISMATCH'
        reason_codes.append(STATE_SESSION_MISMATCH)
        examples.append(
            {
                'source_layer': 'session_binding',
                'observed_state': funnel_session_detected,
                'expected_state': portfolio_session_detected,
                'session_key': funnel_session_detected,
                'reason_code': STATE_SESSION_MISMATCH,
            }
        )

    if funnel_scope and portfolio_scope and funnel_scope != portfolio_scope:
        state_scope_alignment = 'MISMATCH'
        reason_codes.append(STATE_SCOPE_MISMATCH)
        examples.append(
            {
                'source_layer': 'scope_binding',
                'observed_state': funnel_scope,
                'expected_state': portfolio_scope,
                'session_key': funnel_session_detected or portfolio_session_detected,
                'reason_code': STATE_SCOPE_MISMATCH,
            }
        )

    if portfolio_active and current_window_empty:
        state_window_alignment = 'MISMATCH'
        reason_codes.extend([STATE_PORTFOLIO_ACTIVE_BUT_FUNNEL_EMPTY, STATE_WINDOW_MISMATCH])
        examples.append(
            {
                'source_layer': 'funnel_snapshot',
                'observed_state': 'empty_window',
                'expected_state': 'active_portfolio',
                'session_key': funnel_session_detected or portfolio_session_detected,
                'reason_code': STATE_PORTFOLIO_ACTIVE_BUT_FUNNEL_EMPTY,
            }
        )

    if current_window_empty and str(funnel.get('funnel_status') or '').upper() == 'STALLED':
        reason_codes.append(STATE_EMPTY_FALLBACK_APPLIED)
        examples.append(
            {
                'source_layer': 'funnel_status',
                'observed_state': 'STALLED',
                'expected_state': 'derived_from_current_operational_scope',
                'session_key': funnel_session_detected,
                'reason_code': STATE_EMPTY_FALLBACK_APPLIED,
            }
        )

    if stale_view_gate_blocked:
        reason_codes.append(STATE_GATE_BLOCKED_ON_STALE_VIEW)
        examples.append(
            {
                'source_layer': 'gate',
                'observed_state': 'BLOCK',
                'expected_state': 'non-blocking-funnel-check',
                'session_key': funnel_session_detected or portfolio_session_detected,
                'reason_code': STATE_GATE_BLOCKED_ON_STALE_VIEW,
            }
        )

    unique_reason_codes = list(dict.fromkeys(reason_codes))
    if not unique_reason_codes:
        unique_reason_codes = [STATE_ALIGNMENT_OK]

    consistency_status = 'ALIGNED' if unique_reason_codes == [STATE_ALIGNMENT_OK] else 'MISMATCH'
    summary = {
        'consistency_status': consistency_status,
        'state_consistency_status': consistency_status,
        'funnel_session_detected': funnel_session_detected or 'UNKNOWN',
        'portfolio_session_detected': portfolio_session_detected or 'UNKNOWN',
        'state_window_alignment': state_window_alignment,
        'state_scope_alignment': state_scope_alignment if session_alignment == 'ALIGNED' else 'MISMATCH',
        'state_consistency_reason_codes': unique_reason_codes,
    }
    return StateConsistencySnapshot(
        summary=summary,
        examples=examples[:3],
        reason_codes=unique_reason_codes,
        should_ignore_funnel_block=(
            recent_trades_count > 0 and current_window_empty and session_alignment == 'ALIGNED' and (state_scope_alignment == 'ALIGNED')
        ),
    )
