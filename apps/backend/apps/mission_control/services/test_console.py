from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from threading import Lock
from typing import Any

from django.utils import timezone

from apps.mission_control.models import AutonomousRuntimeSession, AutonomousRuntimeSessionStatus
from apps.mission_control.services.execution_exposure_diagnostics import (
    TEST_CONSOLE_EXPORT_PARTIAL_DIAGNOSTIC_RECOVERED,
    TEST_CONSOLE_EXPOSURE_DIAGNOSTIC_FALLBACK_USED,
    normalize_execution_exposure_diagnostics,
)
from apps.mission_control.services.extended_paper_run_gate import GATE_ALLOW, GATE_ALLOW_WITH_CAUTION, build_extended_paper_run_gate
from apps.mission_control.services.extended_paper_run_launcher import get_extended_paper_run_status, launch_extended_paper_run
from apps.mission_control.services.live_paper_attention_bridge import get_live_paper_attention_alert_status
from apps.mission_control.services.live_paper_autonomy_funnel import build_live_paper_autonomy_funnel_snapshot
from apps.mission_control.services.live_paper_bootstrap import (
    MARKET_DATA_MODE_REAL_READ_ONLY,
    PAPER_EXECUTION_MODE_PAPER_ONLY,
    PRESET_NAME,
    bootstrap_live_read_only_paper_session,
    get_live_paper_bootstrap_status,
)
from apps.mission_control.services.live_paper_trial_run import run_live_paper_trial_run
from apps.mission_control.services.live_paper_trial_trend import build_live_paper_trial_trend_digest
from apps.mission_control.services.live_paper_validation import build_live_paper_validation_digest
from apps.mission_control.services.llm_aux_signal import build_llm_aux_signal_summary
from apps.mission_control.services.llm_shadow import build_llm_shadow_summary
from apps.mission_control.services.session_heartbeat import get_runner_state, pause_runner
from apps.mission_control.services.session_runtime import pause_session
from apps.mission_control.services.state_consistency import build_state_consistency_snapshot
from apps.paper_trading.services.portfolio import build_account_financial_summary, build_account_summary, get_active_account
from apps.research_agent.models import NarrativeSignal, NarrativeSignalStatus, SourceScanRun
from apps.research_agent.services.intelligence_handoff.run import run_consensus_review
from apps.research_agent.services.pursuit_scoring.run import run_pursuit_review
from apps.research_agent.services.run import run_scan_agent

TEST_STATUS_IDLE = 'IDLE'
TEST_STATUS_RUNNING = 'RUNNING'
TEST_STATUS_STOPPED = 'STOPPED'
TEST_STATUS_COMPLETED = 'COMPLETED'
TEST_STATUS_COMPLETED_WITH_WARNINGS = 'COMPLETED_WITH_WARNINGS'
TEST_STATUS_BLOCKED = 'BLOCKED'
TEST_STATUS_FAILED = 'FAILED'

_PHASES = [
    'bootstrap',
    'scan',
    'consensus_review',
    'pursuit_review',
    'trial',
    'validation',
    'trend',
    'gate',
    'extended_run',
    'finalize',
]

_PHASE_LABELS = {
    'bootstrap': 'Inicializando',
    'scan': 'Scan',
    'consensus_review': 'Handoff',
    'pursuit_review': 'Prediction',
    'trial': 'Execution',
    'validation': 'Risk',
    'trend': 'Risk',
    'gate': 'Risk',
    'extended_run': 'Execution',
    'finalize': 'Finalizando',
}

_HISTORY_SIZE = 10


@dataclass
class _ConsoleState:
    status: dict[str, Any]
    last_log: dict[str, Any] | None
    history: deque[dict[str, Any]]


_state_lock = Lock()
_state = _ConsoleState(
    status={
        'test_status': TEST_STATUS_IDLE,
        'current_phase': None,
        'started_at': None,
        'ended_at': None,
        'preset_name': PRESET_NAME,
        'session_active': False,
        'heartbeat_active': False,
        'current_session_status': 'UNKNOWN',
        'validation_status': 'UNKNOWN',
        'trial_status': 'UNKNOWN',
        'trend_status': 'UNKNOWN',
        'readiness_status': 'UNKNOWN',
        'gate_status': 'UNKNOWN',
        'extended_run_status': 'UNKNOWN',
        'funnel_status': 'UNKNOWN',
        'handoff_summary': {},
        'downstream_route_summary': {},
        'llm_shadow_summary': {
            'provider': 'ollama',
            'model': 'unknown',
            'shadow_only': True,
            'advisory_only': True,
            'non_blocking': True,
            'llm_shadow_reasoning_status': 'UNAVAILABLE',
            'stance': 'unclear',
            'confidence': 'low',
            'summary': 'LLM shadow analysis is not available yet.',
            'key_risks': [],
            'key_supporting_points': [],
            'recommendation_mode': 'observe',
        },
        'latest_llm_shadow_summary': {},
        'llm_shadow_history_count': 0,
        'llm_shadow_recent_history': [],
        'llm_aux_signal_summary': {
            'enabled': False,
            'source_artifact_id': None,
            'aux_signal_status': 'DISABLED',
            'aux_signal_recommendation': 'observe',
            'aux_signal_reason_codes': ['LLM_AUX_SIGNAL_DISABLED'],
            'aux_signal_weight': 0.0,
            'advisory_only': True,
            'affects_execution': False,
            'paper_only': True,
            'real_read_only': True,
        },
        'attention_mode': 'UNKNOWN',
        'portfolio_summary': {},
        'scan_summary': {},
        'state_mismatch_summary': {},
        'state_mismatch_examples': [],
        'blocker_summary': [],
        'next_action_hint': 'Start test console run',
        'warnings': [],
        'errors': [],
        'reason_codes': [],
        'updated_at': timezone.now(),
        'current_step': None,
        'current_step_label': 'Sin etapa',
        'completed_steps': 0,
        'total_steps': len(_PHASES),
        'progress_state': 'idle',
        'elapsed_seconds': None,
        'export_available': False,
        'is_stale': False,
    },
    last_log=None,
    history=deque(maxlen=_HISTORY_SIZE),
)


def _to_float(value: Any) -> float | None:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _int_field(payload: dict[str, Any], key: str) -> int:
    return int(payload.get(key) or 0)


def _str_field(payload: dict[str, Any], key: str) -> str:
    return str(payload.get(key) or '')


def _list_field(payload: dict[str, Any], key: str) -> list[Any]:
    return list(payload.get(key) or [])


def _set_state(*, status: dict[str, Any] | None = None, log: dict[str, Any] | None = None, append_history: bool = False) -> None:
    with _state_lock:
        if status is not None:
            _state.status = deepcopy(status)
        if log is not None:
            _state.last_log = deepcopy(log)
            if append_history:
                _state.history.appendleft(deepcopy(log))


def _phase_index(phase: str | None) -> int:
    if phase in _PHASES:
        return _PHASES.index(phase) + 1
    return 0


def _progress_state_for_status(test_status: str) -> str:
    normalized = str(test_status or TEST_STATUS_IDLE).upper()
    if normalized in {TEST_STATUS_RUNNING, 'IN_PROGRESS', 'ACTIVE'}:
        return 'running'
    if normalized in {TEST_STATUS_COMPLETED, TEST_STATUS_COMPLETED_WITH_WARNINGS}:
        return 'completed'
    if normalized == TEST_STATUS_BLOCKED:
        return 'blocked'
    if normalized == TEST_STATUS_FAILED:
        return 'failed'
    if normalized == TEST_STATUS_STOPPED:
        return 'stopped'
    return 'idle'


def _augment_progress(status_payload: dict[str, Any]) -> dict[str, Any]:
    payload = status_payload
    now = timezone.now()
    current_phase = payload.get('current_phase')
    started_at = payload.get('started_at')
    updated_at = payload.get('updated_at') or payload.get('timestamp') or now
    current_step = _phase_index(current_phase)
    completed_steps = int(sum(1 for item in payload.get('step_results') or [] if item.get('status') in {'ok', 'warning', 'skipped'}))
    total_steps = len(_PHASES)
    if current_step and completed_steps > current_step:
        completed_steps = current_step
    elapsed_seconds = None
    if started_at:
        elapsed_seconds = int(max(0, (now - started_at).total_seconds()))
    stale_seconds = int(max(0, (now - updated_at).total_seconds())) if updated_at else 0
    export_available = bool(payload.get('ended_at') or payload.get('text_export'))
    payload['updated_at'] = updated_at
    payload['current_step'] = current_step if current_step > 0 else None
    payload['current_step_label'] = _PHASE_LABELS.get(current_phase or '', str(current_phase or 'Sin etapa'))
    payload['completed_steps'] = completed_steps
    payload['total_steps'] = total_steps
    payload['progress_state'] = _progress_state_for_status(str(payload.get('test_status') or TEST_STATUS_IDLE))
    payload['elapsed_seconds'] = elapsed_seconds
    payload['export_available'] = export_available
    payload['is_stale'] = stale_seconds > 30 and payload['progress_state'] != 'running'
    return payload


def _get_state_snapshot() -> tuple[dict[str, Any], dict[str, Any] | None, list[dict[str, Any]]]:
    with _state_lock:
        return deepcopy(_state.status), deepcopy(_state.last_log), deepcopy(list(_state.history))


def _find_active_preset_session(*, preset_name: str) -> AutonomousRuntimeSession | None:
    return (
        AutonomousRuntimeSession.objects.filter(
            session_status__in=[AutonomousRuntimeSessionStatus.RUNNING, AutonomousRuntimeSessionStatus.PAUSED]
        )
        .order_by('-updated_at', '-id')
        .filter(metadata__autopilot_preset_name=preset_name)
        .first()
    )


def _build_portfolio_summary() -> dict[str, Any]:
    account = get_active_account()
    summary = build_account_summary(account=account)
    financial = build_account_financial_summary(account=account)
    recent_trades = summary.get('recent_trades') or []
    return {
        'cash': _to_float(financial.get('cash')),
        'equity': _to_float(financial.get('equity')),
        'realized_pnl': _to_float(financial.get('realized_pnl')),
        'unrealized_pnl': _to_float(financial.get('unrealized_pnl')),
        'open_positions': int(summary.get('open_positions_count') or 0),
        'recent_trades_count': len(recent_trades),
        'account_summary_status': str(financial.get('summary_status') or 'PAPER_ACCOUNT_SUMMARY_UNAVAILABLE'),
        'account_summary_reason_codes': list(financial.get('reason_codes') or []),
    }


def _build_scan_summary(scan_run: SourceScanRun | None = None) -> dict[str, Any]:
    latest = scan_run or SourceScanRun.objects.order_by('-started_at', '-id').first()
    if not latest:
        return {
            'runs': 0,
            'rss_items': 0,
            'reddit_items': 0,
            'x_items': 0,
            'deduped_items': 0,
            'clusters': 0,
            'shortlisted_signals': 0,
            'signals_total': 0,
        }

    source_counts = latest.source_counts or {}
    diagnostics = (latest.metadata or {}).get('scan_diagnostics') or {}
    shortlisted_signals = latest.signals.filter(status=NarrativeSignalStatus.SHORTLISTED).count()

    return {
        'runs': SourceScanRun.objects.count(),
        'latest_run_id': latest.id,
        'summary_window': 'latest_scan_run',
        'rss_items': int(source_counts.get('rss_count') or 0),
        'reddit_items': int(source_counts.get('reddit_count') or 0),
        'x_items': int(source_counts.get('x_count') or 0),
        'raw_items': int(latest.raw_item_count or 0),
        'deduped_items': int(latest.deduped_item_count or 0),
        'clusters': int(latest.clustered_count or 0),
        'shortlisted_signals': int(shortlisted_signals),
        'signals_total': int(latest.signal_count or 0),
        'source_mode': str(diagnostics.get('source_mode') or ''),
        'rss_enabled': bool(diagnostics.get('rss_enabled')),
        'reddit_enabled': bool(diagnostics.get('reddit_enabled')),
        'x_enabled': bool(diagnostics.get('x_enabled')),
        'rss_fetch_attempted': bool(diagnostics.get('rss_fetch_attempted')),
        'reddit_fetch_attempted': bool(diagnostics.get('reddit_fetch_attempted')),
        'x_fetch_attempted': bool(diagnostics.get('x_fetch_attempted')),
        'zero_signal_reason_codes': list(diagnostics.get('zero_signal_reason_codes') or []),
        'diagnostic_summary': str(diagnostics.get('diagnostic_summary') or ''),
        'demo_fallback_used': bool((latest.metadata or {}).get('demo_fallback_used')),
        'summary': str(getattr(latest, 'summary', '') or ''),
    }


def _build_portfolio_trade_reconciliation_summary(*, payload: dict[str, Any]) -> dict[str, Any]:
    paper_trade_final = payload.get('paper_trade_final_summary') or {}
    lineage = payload.get('execution_lineage_summary') or {}
    portfolio = payload.get('portfolio_summary') or {}
    missing_numeric_fields: list[str] = []
    fallback_fields: list[str] = []

    def _coerce_int(value: Any, *, field: str) -> int:
        if value is None:
            missing_numeric_fields.append(field)
            fallback_fields.append(field)
            return 0
        try:
            return int(value)
        except (TypeError, ValueError):
            missing_numeric_fields.append(field)
            fallback_fields.append(field)
            return 0

    def _coerce_float(value: Any, *, field: str) -> float:
        converted = _to_float(value)
        if converted is None:
            missing_numeric_fields.append(field)
            fallback_fields.append(field)
            return 0.0
        return float(converted)

    materialized = _coerce_int(lineage.get('trades_materialized') or paper_trade_final.get('created'), field='trades_materialized')
    reused = _coerce_int(lineage.get('trades_reused') or paper_trade_final.get('reused'), field='trades_reused')
    recent_trades_count = _coerce_int(portfolio.get('recent_trades_count'), field='recent_trades_count')
    open_positions = _coerce_int(portfolio.get('open_positions'), field='open_positions')
    equity = _coerce_float(portfolio.get('equity'), field='equity')
    unrealized_pnl = _coerce_float(portfolio.get('unrealized_pnl'), field='unrealized_pnl')
    realized_pnl = _coerce_float(portfolio.get('realized_pnl'), field='realized_pnl')
    reason_codes: list[str] = []
    if recent_trades_count >= min(1, materialized + reused):
        reason_codes.append('PORTFOLIO_SCOPE_ALIGNMENT_OK')
    else:
        reason_codes.append('PORTFOLIO_SCOPE_ALIGNMENT_MISMATCH')
    if materialized + reused > max(recent_trades_count, 1):
        reason_codes.append('PORTFOLIO_TRADE_COUNT_MISMATCH')
    if reused > max(3, materialized * 3) and open_positions <= 1:
        reason_codes.append('PORTFOLIO_POSITION_REUSE_ACCUMULATION')
    if equity > 0 and abs(unrealized_pnl) > (equity * 0.9):
        reason_codes.append('PORTFOLIO_UNREALIZED_PNL_OUTLIER')
    status = 'OK'
    if any(code in reason_codes for code in ['PORTFOLIO_TRADE_COUNT_MISMATCH', 'PORTFOLIO_SCOPE_ALIGNMENT_MISMATCH']):
        status = 'CHECK'
    if missing_numeric_fields:
        status = 'DEGRADED'
        reason_codes.append('PORTFOLIO_TRADE_RECONCILIATION_DEGRADED')
        reason_codes.append('PORTFOLIO_TRADE_RECONCILIATION_MISSING_NUMERIC_FIELD')
    if fallback_fields:
        reason_codes.append('PORTFOLIO_TRADE_RECONCILIATION_FALLBACK_USED')
    if not reason_codes:
        reason_codes.append('PORTFOLIO_TRADE_RECONCILIATION_OK')
    normalized_codes = list(dict.fromkeys(reason_codes))
    if status == 'OK' and normalized_codes == ['PORTFOLIO_SCOPE_ALIGNMENT_OK']:
        normalized_codes.insert(0, 'PORTFOLIO_TRADE_RECONCILIATION_OK')
    return {
        'portfolio_trade_reconciliation_status': status,
        'portfolio_trade_reconciliation_reason_codes': normalized_codes,
        'materialized_paper_trades': materialized,
        'reused_trade_cycles': reused,
        'recent_trades_count': recent_trades_count,
        'open_positions': open_positions,
        'equity': equity,
        'unrealized_pnl': unrealized_pnl,
        'realized_pnl': realized_pnl,
        'missing_numeric_fields': list(dict.fromkeys(missing_numeric_fields)),
        'fallback_fields': list(dict.fromkeys(fallback_fields)),
        'trades_considered': int(materialized + reused),
        'positions_considered': int(open_positions),
        'pnl_considered': {'equity': equity, 'unrealized_pnl': unrealized_pnl, 'realized_pnl': realized_pnl},
        'reconciliation_summary': (
            f"materialized_paper_trades={materialized} reused_trade_cycles={reused} recent_trades_count={recent_trades_count} "
            f"open_positions={open_positions} equity={equity:.2f} unrealized_pnl={unrealized_pnl:.2f} realized_pnl={realized_pnl:.2f} "
            f"portfolio_trade_reconciliation_status={status} "
            f"portfolio_trade_reconciliation_reason_codes={','.join(normalized_codes) or 'none'}"
        ),
    }


def _build_active_operational_overlay_summary(*, payload: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
    handoff = payload.get('handoff_summary') or {}
    portfolio = payload.get('portfolio_summary') or {}
    state_mismatch = payload.get('state_mismatch_summary') or {}
    window_empty = (
        int(handoff.get('shortlisted_signals') or 0) <= 0
        and int(handoff.get('handoff_candidates') or 0) <= 0
        and int(handoff.get('consensus_reviews') or 0) <= 0
        and int(handoff.get('prediction_candidates') or 0) <= 0
        and int(handoff.get('risk_decisions') or 0) <= 0
        and int(handoff.get('paper_execution_candidates') or 0) <= 0
    )
    active_positions_detected = int(portfolio.get('open_positions') or 0) > 0
    active_trades_detected = int(portfolio.get('recent_trades_count') or 0) > 0
    consistency_codes = set(state_mismatch.get('state_consistency_reason_codes') or [])
    active_runtime_context_detected = bool(
        active_positions_detected
        or active_trades_detected
        or 'STATE_PORTFOLIO_ACTIVE_BUT_FUNNEL_EMPTY' in consistency_codes
        or 'STATE_WINDOW_MISMATCH' in consistency_codes
    )

    reason_codes: list[str] = []
    if window_empty and active_runtime_context_detected:
        reason_codes.append('ACTIVE_OVERLAY_APPLIED')
        if active_positions_detected:
            reason_codes.append('ACTIVE_OVERLAY_POSITION_PRESENT')
        if active_trades_detected:
            reason_codes.append('ACTIVE_OVERLAY_RECENT_TRADES_PRESENT')
        if active_runtime_context_detected:
            reason_codes.append('ACTIVE_OVERLAY_RUNTIME_CONTEXT_PRESENT')
        overlay_status = 'APPLIED'
        effective_funnel_status = 'ACTIVE_WITHOUT_RECENT_FLOW'
        overlay_summary = (
            'Rolling window sin flujo reciente, pero el estado operativo sigue activo '
            f'(open_positions={int(portfolio.get("open_positions") or 0)}, '
            f'recent_trades_count={int(portfolio.get("recent_trades_count") or 0)}).'
        )
    else:
        reason_codes.append('ACTIVE_OVERLAY_NOT_APPLIED')
        overlay_status = 'NOT_APPLIED'
        effective_funnel_status = str(payload.get('funnel_status') or 'UNKNOWN')
        overlay_summary = 'No se aplicó carry-forward operativo; el estado refleja solo la actividad de la ventana.'

    return (
        {
            'overlay_status': overlay_status,
            'active_positions_detected': bool(active_positions_detected),
            'active_trades_detected': bool(active_trades_detected),
            'active_runtime_context_detected': bool(active_runtime_context_detected),
            'active_operational_overlay_reason_codes': reason_codes,
            'overlay_summary': overlay_summary,
        },
        effective_funnel_status,
        overlay_summary,
    )


def _sync_operational_snapshot(*, payload: dict[str, Any], preset_name: str, scan_run: SourceScanRun | None = None) -> None:
    bootstrap_status = get_live_paper_bootstrap_status(preset_name=preset_name)
    validation = build_live_paper_validation_digest(preset_name=preset_name)
    trend = build_live_paper_trial_trend_digest(limit=5, preset=preset_name)
    gate = build_extended_paper_run_gate(preset_name=preset_name)
    extended = get_extended_paper_run_status(preset_name=preset_name)
    attention = get_live_paper_attention_alert_status()
    funnel: dict[str, Any]
    try:
        funnel = build_live_paper_autonomy_funnel_snapshot(window_minutes=60, preset_name=preset_name)
    except (NameError, KeyError, UnboundLocalError):
        funnel = {}
        payload.setdefault('warnings', []).append(TEST_CONSOLE_EXPOSURE_DIAGNOSTIC_FALLBACK_USED)
        payload.setdefault('reason_codes', []).append(TEST_CONSOLE_EXPOSURE_DIAGNOSTIC_FALLBACK_USED)

    exposure_diagnostics = normalize_execution_exposure_diagnostics(
        provenance_summary=funnel.get('execution_exposure_provenance_summary'),
        provenance_examples=funnel.get('execution_exposure_provenance_examples'),
        release_audit_summary=funnel.get('execution_exposure_release_audit_summary'),
        release_audit_examples=funnel.get('execution_exposure_release_audit_examples'),
    )
    if exposure_diagnostics.get('fallback_used'):
        payload.setdefault('warnings', []).append(TEST_CONSOLE_EXPOSURE_DIAGNOSTIC_FALLBACK_USED)
        payload.setdefault('reason_codes', []).append(TEST_CONSOLE_EXPOSURE_DIAGNOSTIC_FALLBACK_USED)

    payload.update(
        {
            'session_active': bool(bootstrap_status.get('session_active')),
            'heartbeat_active': bool(bootstrap_status.get('heartbeat_active')),
            'current_session_status': str(bootstrap_status.get('current_session_status') or 'UNKNOWN'),
            'validation_status': str(validation.get('validation_status') or 'UNKNOWN'),
            'trend_status': str(trend.get('trend_status') or 'UNKNOWN'),
            'readiness_status': str(trend.get('readiness_status') or 'UNKNOWN'),
            'gate_status': str(gate.get('gate_status') or 'UNKNOWN'),
            'extended_run_status': 'ACTIVE' if bool(extended.get('extended_run_active')) else str(extended.get('gate_status') or 'INACTIVE'),
            'funnel_status': str(funnel.get('funnel_status') or 'UNKNOWN'),
            'handoff_summary': {
                'summary_window': f"rolling_{int(funnel.get('window_minutes') or 60)}m",
                'shortlisted_signals': int(funnel.get('shortlisted_signals') or 0),
                'handoff_candidates': int(funnel.get('handoff_candidates') or 0),
                'consensus_reviews': int(funnel.get('consensus_reviews') or 0),
                'prediction_candidates': int(funnel.get('prediction_candidates') or 0),
                'risk_decisions': int(funnel.get('risk_decisions') or 0),
                'paper_execution_candidates': int(funnel.get('paper_execution_candidates') or 0),
                'handoff_reason_codes': list(funnel.get('handoff_reason_codes') or []),
            },
            'paper_execution_summary': {
                'route_expected': _int_field(funnel, 'paper_execution_route_expected'),
                'route_available': _int_field(funnel, 'paper_execution_route_available'),
                'route_attempted': _int_field(funnel, 'paper_execution_route_attempted'),
                'route_created': _int_field(funnel, 'paper_execution_route_created'),
                'route_reused': _int_field(funnel, 'paper_execution_route_reused'),
                'route_blocked': _int_field(funnel, 'paper_execution_route_blocked'),
                'route_missing_status_count': _int_field(funnel, 'paper_execution_route_missing_status_count'),
                'paper_execution_route_reason_codes': _list_field(funnel, 'paper_execution_route_reason_codes'),
                'paper_execution_summary': _str_field(funnel, 'paper_execution_summary'),
            },
            'paper_execution_examples': list(funnel.get('paper_execution_examples') or []),
            'paper_execution_visibility_summary': {
                'created': _int_field(funnel, 'paper_execution_created_count'),
                'reused': _int_field(funnel, 'paper_execution_reused_count'),
                'visible': _int_field(funnel, 'paper_execution_visible_count'),
                'hidden': _int_field(funnel, 'paper_execution_hidden_count'),
                'paper_execution_visibility_reason_codes': _list_field(funnel, 'paper_execution_visibility_reason_codes'),
                'paper_execution_visibility_summary': _str_field(funnel, 'paper_execution_visibility_summary'),
                'measurement_scope': 'execution_intake_candidate_visibility_window',
                'source_of_truth': 'autonomous_execution_intake_candidate',
                'explains_pre_creation_suppression': True,
            },
            'paper_execution_visibility_examples': list(funnel.get('paper_execution_visibility_examples') or []),
            'paper_trade_summary': {
                'route_expected': _int_field(funnel, 'paper_trade_route_expected'),
                'route_available': _int_field(funnel, 'paper_trade_route_available'),
                'route_attempted': _int_field(funnel, 'paper_trade_route_attempted'),
                'route_created': _int_field(funnel, 'paper_trade_route_created'),
                'route_reused': _int_field(funnel, 'paper_trade_route_reused'),
                'route_blocked': _int_field(funnel, 'paper_trade_route_blocked'),
                'paper_trade_route_reason_codes': _list_field(funnel, 'paper_trade_route_reason_codes'),
                'paper_trade_summary': _str_field(funnel, 'paper_trade_summary'),
            },
            'paper_trade_examples': list(funnel.get('paper_trade_examples') or []),
            'paper_trade_decision_summary': {
                'route_expected': _int_field(funnel, 'paper_trade_route_expected'),
                'decision_created': _int_field(funnel, 'paper_trade_decision_created'),
                'decision_reused': _int_field(funnel, 'paper_trade_decision_reused'),
                'decision_blocked': _int_field(funnel, 'paper_trade_decision_blocked'),
                'decision_dedupe_applied': _int_field(funnel, 'paper_trade_decision_dedupe_applied'),
                'paper_trade_decision_reason_codes': _list_field(funnel, 'paper_trade_decision_reason_codes'),
                'paper_trade_decision_summary': _str_field(funnel, 'paper_trade_decision_summary'),
            },
            'paper_trade_decision_examples': list(funnel.get('paper_trade_decision_examples') or []),
            'paper_trade_dispatch_summary': {
                'route_expected': _int_field(funnel, 'paper_trade_route_expected'),
                'dispatch_created': _int_field(funnel, 'paper_trade_dispatch_created'),
                'dispatch_reused': _int_field(funnel, 'paper_trade_dispatch_reused'),
                'dispatch_blocked': _int_field(funnel, 'paper_trade_dispatch_blocked'),
                'dispatch_dedupe_applied': _int_field(funnel, 'paper_trade_dispatch_dedupe_applied'),
                'paper_trade_dispatch_reason_codes': _list_field(funnel, 'paper_trade_dispatch_reason_codes'),
                'paper_trade_dispatch_summary': _str_field(funnel, 'paper_trade_dispatch_summary'),
            },
            'paper_trade_dispatch_examples': list(funnel.get('paper_trade_dispatch_examples') or []),
            'paper_trade_final_summary': {
                'expected': _int_field(funnel, 'final_trade_expected'),
                'available': _int_field(funnel, 'final_trade_available'),
                'attempted': _int_field(funnel, 'final_trade_attempted'),
                'created': _int_field(funnel, 'final_trade_created'),
                'reused': _int_field(funnel, 'final_trade_reused'),
                'blocked': _int_field(funnel, 'final_trade_blocked'),
                'final_trade_reason_codes': _list_field(funnel, 'final_trade_reason_codes'),
                'runtime_rejection_summary': _str_field(funnel, 'runtime_rejection_summary'),
                'runtime_rejection_reason_codes': _list_field(funnel, 'runtime_rejection_reason_codes'),
                'paper_trade_final_summary': _str_field(funnel, 'paper_trade_final_summary'),
            },
            'paper_trade_final_examples': list(funnel.get('paper_trade_final_examples') or []),
            'execution_candidate_creation_gate_summary': dict(funnel.get('execution_candidate_creation_gate_summary') or {}),
            'execution_candidate_creation_gate_examples': list(funnel.get('execution_candidate_creation_gate_examples') or []),
            'execution_exposure_provenance_summary': dict(exposure_diagnostics.get('execution_exposure_provenance_summary') or {}),
            'execution_exposure_provenance_examples': list(exposure_diagnostics.get('execution_exposure_provenance_examples') or []),
            'execution_exposure_release_audit_summary': dict(exposure_diagnostics.get('execution_exposure_release_audit_summary') or {}),
            'execution_exposure_release_audit_examples': list(exposure_diagnostics.get('execution_exposure_release_audit_examples') or []),
            'active_exposure_readiness_throttle_summary': dict(funnel.get('active_exposure_readiness_throttle_summary') or {}),
            'active_exposure_readiness_throttle_examples': list(funnel.get('active_exposure_readiness_throttle_examples') or []),
            'execution_promotion_gate_summary': dict(funnel.get('execution_promotion_gate_summary') or {}),
            'execution_promotion_gate_examples': list(funnel.get('execution_promotion_gate_examples') or []),
            'execution_lineage_summary': dict(funnel.get('execution_lineage_summary') or {}),
            'final_fanout_summary': dict(funnel.get('final_fanout_summary') or {}),
            'final_fanout_examples': list(funnel.get('final_fanout_examples') or []),
            'cash_pressure_summary': dict(funnel.get('cash_pressure_summary') or {}),
            'cash_pressure_examples': list(funnel.get('cash_pressure_examples') or []),
            'position_exposure_summary': dict(funnel.get('position_exposure_summary') or {}),
            'execution_artifact_summary': {
                'execution_readiness_available_count': int(funnel.get('execution_readiness_available_count') or 0),
                'readiness_created': int(funnel.get('execution_readiness_created_count') or 0),
                'readiness_reused': int(funnel.get('execution_readiness_reused_count') or 0),
                'candidate_created': int(funnel.get('execution_candidate_created_count') or 0),
                'candidate_reused': int(funnel.get('execution_candidate_reused_count') or 0),
                'candidate_visible': int(funnel.get('execution_candidate_visible_count') or 0),
                'candidate_hidden': int(funnel.get('execution_candidate_hidden_count') or 0),
                'execution_artifact_blocked_count': int(funnel.get('execution_artifact_blocked_count') or 0),
                'execution_artifact_reason_codes': list(funnel.get('execution_artifact_reason_codes') or []),
                'execution_artifact_summary': str(funnel.get('execution_artifact_summary') or ''),
                'measurement_scope': 'readiness_and_candidate_artifacts',
                'source_of_truth': 'autonomous_execution_readiness_and_intake_candidate',
                'explains_pre_creation_suppression': True,
            },
            'execution_artifact_examples': list(funnel.get('execution_artifact_examples') or []),
            'shortlist_handoff_summary': dict(funnel.get('shortlist_handoff_summary') or {}),
            'downstream_route_summary': dict(funnel.get('downstream_route_summary') or {}),
            'downstream_route_examples': list(funnel.get('downstream_route_examples') or []),
            'market_link_summary': dict(funnel.get('market_link_summary') or {}),
            'market_link_examples': list(funnel.get('market_link_examples') or []),
            'consensus_alignment': dict(funnel.get('consensus_alignment') or {}),
            'handoff_scoring_summary': dict(funnel.get('handoff_scoring_summary') or {}),
            'handoff_scoring_examples': list(funnel.get('handoff_scoring_examples') or []),
            'handoff_borderline_summary': dict(funnel.get('handoff_borderline_summary') or {}),
            'handoff_borderline_examples': list(funnel.get('handoff_borderline_examples') or []),
            'handoff_structural_summary': dict(funnel.get('handoff_structural_summary') or {}),
            'handoff_structural_examples': list(funnel.get('handoff_structural_examples') or []),
            'prediction_intake_summary': dict(funnel.get('prediction_intake_summary') or {}),
            'prediction_intake_examples': list(funnel.get('prediction_intake_examples') or []),
            'prediction_visibility_summary': dict(funnel.get('prediction_visibility_summary') or {}),
            'prediction_visibility_examples': list(funnel.get('prediction_visibility_examples') or []),
            'prediction_artifact_summary': dict(funnel.get('prediction_artifact_summary') or {}),
            'prediction_artifact_examples': list(funnel.get('prediction_artifact_examples') or []),
            'prediction_risk_summary': dict(funnel.get('prediction_risk_summary') or {}),
            'prediction_risk_examples': list(funnel.get('prediction_risk_examples') or []),
            'prediction_risk_caution_summary': dict(funnel.get('prediction_risk_caution_summary') or {}),
            'prediction_risk_caution_examples': list(funnel.get('prediction_risk_caution_examples') or []),
            'prediction_status_summary': dict(funnel.get('prediction_status_summary') or {}),
            'prediction_status_examples': list(funnel.get('prediction_status_examples') or []),
            'attention_mode': str(attention.get('attention_mode') or 'UNKNOWN'),
            'portfolio_summary': _build_portfolio_summary(),
            'scan_summary': _build_scan_summary(scan_run=scan_run),
            'next_action_hint': str(gate.get('next_action_hint') or validation.get('next_action_hint') or 'Review test console log'),
            'reason_codes': list(
                dict.fromkeys(
                    list(gate.get('reason_codes') or [])
                    + list(payload.get('reason_codes') or [])
                )
            ),
            'runtime_rejection_summary': str(funnel.get('runtime_rejection_summary') or ''),
            'runtime_rejection_reason_codes': list(funnel.get('runtime_rejection_reason_codes') or []),
        }
    )
    payload['portfolio_trade_reconciliation_summary'] = _build_portfolio_trade_reconciliation_summary(payload=payload)
    payload['llm_shadow_summary'] = build_llm_shadow_summary(payload=payload, funnel=funnel)
    payload['latest_llm_shadow_summary'] = dict(payload['llm_shadow_summary'].get('latest_llm_shadow_summary') or payload['llm_shadow_summary'])
    payload['llm_shadow_history_count'] = int(payload['llm_shadow_summary'].get('llm_shadow_history_count') or 0)
    payload['llm_shadow_recent_history'] = list(payload['llm_shadow_summary'].get('llm_shadow_recent_history') or [])
    payload['llm_aux_signal_summary'] = build_llm_aux_signal_summary(payload=payload)
    payload['reconciliation_status'] = str(payload['portfolio_trade_reconciliation_summary'].get('portfolio_trade_reconciliation_status') or 'UNKNOWN')
    payload['reconciliation_reason_codes'] = list(payload['portfolio_trade_reconciliation_summary'].get('portfolio_trade_reconciliation_reason_codes') or [])
    active_session = _find_active_preset_session(preset_name=preset_name)
    portfolio = payload.get('portfolio_summary') or {}
    account = get_active_account()
    consistency = build_state_consistency_snapshot(
        funnel=funnel,
        portfolio_summary=portfolio,
        funnel_session_detected=(f"runtime_session:{active_session.id}" if active_session else None),
        portfolio_session_detected=f"paper_account:{account.slug}",
        funnel_scope=None,
        portfolio_scope=None,
        stale_view_gate_blocked=bool(payload.get('gate_status') == 'BLOCK' and int(portfolio.get('open_positions') or 0) > 0 and str(funnel.get('funnel_status') or '').upper() == 'STALLED'),
    )
    payload['state_mismatch_summary'] = consistency.summary
    payload['state_mismatch_examples'] = consistency.examples
    overlay_summary, effective_funnel_status, overlay_text = _build_active_operational_overlay_summary(payload=payload)
    payload['active_operational_overlay_summary'] = overlay_summary
    position_exposure = dict(payload.get('position_exposure_summary') or {})
    creation_gate = dict(payload.get('execution_candidate_creation_gate_summary') or {})
    position_exposure_codes = list(position_exposure.get('position_exposure_reason_codes') or [])
    if bool(overlay_summary.get('active_runtime_context_detected')) and int(position_exposure.get('open_positions_detected') or 0) <= 0:
        position_exposure_codes.append('ACTIVE_OVERLAY_FROM_PORTFOLIO_BUT_NO_FINAL_POSITION_GATE_BLOCK')
    if int(creation_gate.get('candidates_suppressed_before_creation') or 0) > 0 and int(position_exposure.get('open_positions_detected') or 0) <= 0:
        position_exposure_codes.append('POSITION_EXPOSURE_SCOPE_DIFFERS_FROM_CREATION_GATE')
    if position_exposure_codes:
        position_exposure['position_exposure_reason_codes'] = list(dict.fromkeys(position_exposure_codes))
        payload['position_exposure_summary'] = position_exposure
    payload['funnel_status_window'] = str(funnel.get('funnel_status') or 'UNKNOWN')
    payload['funnel_status'] = effective_funnel_status
    payload['summary'] = (
        f"funnel_status={payload.get('funnel_status')} window_funnel_status={payload.get('funnel_status_window')} "
        f"overlay_status={overlay_summary.get('overlay_status')} gate_status={payload.get('gate_status')}. "
        f"{overlay_text}"
    )


def _log_line_items(payload: dict[str, Any]) -> str:
    scan = payload.get('scan_summary') or {}
    portfolio = payload.get('portfolio_summary') or {}
    warnings = payload.get('warnings') or []
    errors = payload.get('errors') or []
    blockers = payload.get('blocker_summary') or []
    handoff_summary = payload.get('handoff_summary') or {}
    paper_execution = payload.get('paper_execution_summary') or {}
    paper_execution_examples = payload.get('paper_execution_examples') or []
    paper_execution_visibility = payload.get('paper_execution_visibility_summary') or {}
    paper_execution_visibility_examples = payload.get('paper_execution_visibility_examples') or []
    paper_trade = payload.get('paper_trade_summary') or {}
    paper_trade_examples = payload.get('paper_trade_examples') or []
    paper_trade_decision = payload.get('paper_trade_decision_summary') or {}
    paper_trade_decision_examples = payload.get('paper_trade_decision_examples') or []
    paper_trade_dispatch = payload.get('paper_trade_dispatch_summary') or {}
    paper_trade_dispatch_examples = payload.get('paper_trade_dispatch_examples') or []
    paper_trade_final = payload.get('paper_trade_final_summary') or {}
    paper_trade_final_examples = payload.get('paper_trade_final_examples') or []
    execution_creation_gate = payload.get('execution_candidate_creation_gate_summary') or {}
    execution_creation_gate_examples = payload.get('execution_candidate_creation_gate_examples') or []
    exposure_diagnostics = normalize_execution_exposure_diagnostics(
        provenance_summary=payload.get('execution_exposure_provenance_summary'),
        provenance_examples=payload.get('execution_exposure_provenance_examples'),
        release_audit_summary=payload.get('execution_exposure_release_audit_summary'),
        release_audit_examples=payload.get('execution_exposure_release_audit_examples'),
    )
    execution_exposure_provenance = exposure_diagnostics.get('execution_exposure_provenance_summary') or {}
    execution_exposure_provenance_examples = exposure_diagnostics.get('execution_exposure_provenance_examples') or []
    execution_exposure_release_audit = exposure_diagnostics.get('execution_exposure_release_audit_summary') or {}
    execution_exposure_release_audit_examples = exposure_diagnostics.get('execution_exposure_release_audit_examples') or []
    active_exposure_readiness_throttle = payload.get('active_exposure_readiness_throttle_summary') or {}
    active_exposure_readiness_throttle_examples = payload.get('active_exposure_readiness_throttle_examples') or []
    execution_promotion_gate = payload.get('execution_promotion_gate_summary') or {}
    execution_promotion_gate_examples = payload.get('execution_promotion_gate_examples') or []
    execution_lineage = payload.get('execution_lineage_summary') or {}
    final_fanout = payload.get('final_fanout_summary') or {}
    final_fanout_examples = payload.get('final_fanout_examples') or []
    cash_pressure = payload.get('cash_pressure_summary') or {}
    cash_pressure_examples = payload.get('cash_pressure_examples') or []
    position_exposure = payload.get('position_exposure_summary') or {}
    portfolio_trade_reconciliation = payload.get('portfolio_trade_reconciliation_summary') or {}
    execution_artifact = payload.get('execution_artifact_summary') or {}
    execution_artifact_examples = payload.get('execution_artifact_examples') or []
    shortlist_handoff = payload.get('shortlist_handoff_summary') or {}
    downstream_route = payload.get('downstream_route_summary') or {}
    downstream_route_examples = payload.get('downstream_route_examples') or []
    market_link = payload.get('market_link_summary') or {}
    market_link_examples = payload.get('market_link_examples') or []
    consensus_alignment = payload.get('consensus_alignment') or {}
    handoff_scoring = payload.get('handoff_scoring_summary') or {}
    handoff_scoring_examples = payload.get('handoff_scoring_examples') or []
    handoff_borderline = payload.get('handoff_borderline_summary') or {}
    handoff_borderline_examples = payload.get('handoff_borderline_examples') or []
    handoff_structural = payload.get('handoff_structural_summary') or {}
    handoff_structural_examples = payload.get('handoff_structural_examples') or []
    prediction_intake = payload.get('prediction_intake_summary') or {}
    prediction_intake_examples = payload.get('prediction_intake_examples') or []
    prediction_visibility = payload.get('prediction_visibility_summary') or {}
    prediction_visibility_examples = payload.get('prediction_visibility_examples') or []
    prediction_artifact = payload.get('prediction_artifact_summary') or {}
    prediction_artifact_examples = payload.get('prediction_artifact_examples') or []
    prediction_risk = payload.get('prediction_risk_summary') or {}
    prediction_risk_examples = payload.get('prediction_risk_examples') or []
    prediction_risk_caution = payload.get('prediction_risk_caution_summary') or {}
    prediction_risk_caution_examples = payload.get('prediction_risk_caution_examples') or []
    prediction_status = payload.get('prediction_status_summary') or {}
    prediction_status_examples = payload.get('prediction_status_examples') or []
    state_mismatch_summary = payload.get('state_mismatch_summary') or {}
    state_mismatch_examples = payload.get('state_mismatch_examples') or []
    active_operational_overlay = payload.get('active_operational_overlay_summary') or {}
    llm_shadow = payload.get('llm_shadow_summary') or {}
    llm_aux_signal = payload.get('llm_aux_signal_summary') or {}

    lines = [
        '=== Mission Control Test Console Export ===',
        f"timestamp: {payload.get('timestamp')}",
        f"preset: {payload.get('preset_name')}",
        f"test_status: {payload.get('test_status')}",
        f"current_phase: {payload.get('current_phase')}",
        f"validation_status: {payload.get('validation_status')}",
        f"trial_status: {payload.get('trial_status')}",
        f"trend_status: {payload.get('trend_status')}",
        f"readiness_status: {payload.get('readiness_status')}",
        f"gate_status: {payload.get('gate_status')}",
        f"extended_run_status: {payload.get('extended_run_status')}",
        f"session_active: {payload.get('session_active')}",
        f"heartbeat_active: {payload.get('heartbeat_active')}",
        f"current_session_status: {payload.get('current_session_status')}",
        f"attention_mode: {payload.get('attention_mode')}",
        f"funnel_status: {payload.get('funnel_status')}",
        f"funnel_status_window: {payload.get('funnel_status_window') or payload.get('funnel_status')}",
        'active_operational_overlay_summary:',
        f"  overlay_status={active_operational_overlay.get('overlay_status') or 'UNKNOWN'}",
        (
            f"  active_positions_detected={bool(active_operational_overlay.get('active_positions_detected'))} "
            f"active_trades_detected={bool(active_operational_overlay.get('active_trades_detected'))} "
            f"active_runtime_context_detected={bool(active_operational_overlay.get('active_runtime_context_detected'))}"
        ),
        (
            f"  active_operational_overlay_reason_codes="
            f"{','.join(active_operational_overlay.get('active_operational_overlay_reason_codes') or []) or 'none'}"
        ),
        f"  overlay_summary={active_operational_overlay.get('overlay_summary') or ''}",
        'state_mismatch_summary:',
        f"  consistency_status={state_mismatch_summary.get('consistency_status') or 'UNKNOWN'}",
        f"  funnel_session_detected={state_mismatch_summary.get('funnel_session_detected') or 'UNKNOWN'}",
        f"  portfolio_session_detected={state_mismatch_summary.get('portfolio_session_detected') or 'UNKNOWN'}",
        f"  state_window_alignment={state_mismatch_summary.get('state_window_alignment') or 'UNKNOWN'}",
        f"  state_scope_alignment={state_mismatch_summary.get('state_scope_alignment') or 'UNKNOWN'}",
        (
            f"  state_consistency_reason_codes="
            f"{','.join(state_mismatch_summary.get('state_consistency_reason_codes') or []) or 'none'}"
        ),
        f"  state_mismatch_examples={state_mismatch_examples}",
        'handoff_summary:',
        f"  summary_window={handoff_summary.get('summary_window') or 'rolling_60m'}",
        (
            f"  shortlisted_signals={handoff_summary.get('shortlisted_signals', 0)} "
            f"handoff_candidates={handoff_summary.get('handoff_candidates', 0)} "
            f"consensus_reviews={handoff_summary.get('consensus_reviews', 0)} "
            f"prediction_candidates={handoff_summary.get('prediction_candidates', 0)} "
            f"risk_decisions={handoff_summary.get('risk_decisions', 0)} "
            f"paper_execution_candidates={handoff_summary.get('paper_execution_candidates', 0)}"
        ),
        f"  handoff_reason_codes={','.join(handoff_summary.get('handoff_reason_codes') or []) or 'none'}",
        'llm_shadow_summary:',
        f"  provider={llm_shadow.get('provider') or 'ollama'} model={llm_shadow.get('model') or 'unknown'}",
        f"  llm_shadow_reasoning_status={llm_shadow.get('llm_shadow_reasoning_status') or 'UNAVAILABLE'}",
        (
            f"  shadow_only={bool(llm_shadow.get('shadow_only', True))} "
            f"advisory_only={bool(llm_shadow.get('advisory_only', True))} "
            f"non_blocking={bool(llm_shadow.get('non_blocking', True))}"
        ),
        (
            f"  stance={llm_shadow.get('stance') or 'unclear'} "
            f"confidence={llm_shadow.get('confidence') or 'low'} "
            f"recommendation_mode={llm_shadow.get('recommendation_mode') or 'observe'}"
        ),
        f"  summary={llm_shadow.get('summary') or ''}",
        f"  key_risks={llm_shadow.get('key_risks') or []}",
        f"  key_supporting_points={llm_shadow.get('key_supporting_points') or []}",
        f"  history_count={payload.get('llm_shadow_history_count') or 0}",
        f"  artifact_id={llm_shadow.get('artifact_id')}",
        'llm_aux_signal_summary:',
        f"  enabled={bool(llm_aux_signal.get('enabled', False))}",
        f"  source_artifact_id={llm_aux_signal.get('source_artifact_id')}",
        f"  aux_signal_status={llm_aux_signal.get('aux_signal_status') or 'DISABLED'}",
        f"  aux_signal_recommendation={llm_aux_signal.get('aux_signal_recommendation') or 'observe'}",
        (
            f"  aux_signal_reason_codes="
            f"{','.join(llm_aux_signal.get('aux_signal_reason_codes') or []) or 'none'}"
        ),
        f"  aux_signal_weight={llm_aux_signal.get('aux_signal_weight') if llm_aux_signal else 0.0}",
        (
            f"  advisory_only={bool(llm_aux_signal.get('advisory_only', True))} "
            f"affects_execution={bool(llm_aux_signal.get('affects_execution', False))} "
            f"paper_only={bool(llm_aux_signal.get('paper_only', True))}"
        ),
        'paper_execution_summary:',
        (
            f"  route_expected={paper_execution.get('route_expected', 0)} "
            f"route_available={paper_execution.get('route_available', 0)} "
            f"route_attempted={paper_execution.get('route_attempted', 0)} "
            f"route_created={paper_execution.get('route_created', 0)} "
            f"route_reused={paper_execution.get('route_reused', 0)} "
            f"route_blocked={paper_execution.get('route_blocked', 0)} "
            f"route_missing_status_count={paper_execution.get('route_missing_status_count', 0)}"
        ),
        (
            f"  paper_execution_route_reason_codes="
            f"{','.join(paper_execution.get('paper_execution_route_reason_codes') or []) or 'none'}"
        ),
        f"  paper_execution_examples={paper_execution_examples or []}",
        'paper_execution_visibility_summary:',
        (
            f"  created={paper_execution_visibility.get('created', 0)} "
            f"reused={paper_execution_visibility.get('reused', 0)} "
            f"visible={paper_execution_visibility.get('visible', 0)} "
            f"hidden={paper_execution_visibility.get('hidden', 0)}"
        ),
        (
            f"  paper_execution_visibility_reason_codes="
            f"{','.join(paper_execution_visibility.get('paper_execution_visibility_reason_codes') or []) or 'none'}"
        ),
        (
            f"  measurement_scope={paper_execution_visibility.get('measurement_scope') or 'execution_intake_candidate_visibility_window'} "
            f"source_of_truth={paper_execution_visibility.get('source_of_truth') or 'autonomous_execution_intake_candidate'} "
            f"explains_pre_creation_suppression={bool(paper_execution_visibility.get('explains_pre_creation_suppression', True))}"
        ),
        f"  paper_execution_visibility_examples={paper_execution_visibility_examples or []}",
        'paper_trade_summary:',
        (
            f"  route_expected={paper_trade.get('route_expected', 0)} "
            f"route_available={paper_trade.get('route_available', 0)} "
            f"route_attempted={paper_trade.get('route_attempted', 0)} "
            f"route_created={paper_trade.get('route_created', 0)} "
            f"route_reused={paper_trade.get('route_reused', 0)} "
            f"route_blocked={paper_trade.get('route_blocked', 0)}"
        ),
        f"  paper_trade_route_reason_codes={','.join(paper_trade.get('paper_trade_route_reason_codes') or []) or 'none'}",
        f"  paper_trade_examples={paper_trade_examples or []}",
        'paper_trade_decision_summary:',
        (
            f"  route_expected={paper_trade_decision.get('route_expected', 0)} "
            f"decision_created={paper_trade_decision.get('decision_created', 0)} "
            f"decision_reused={paper_trade_decision.get('decision_reused', 0)} "
            f"decision_blocked={paper_trade_decision.get('decision_blocked', 0)} "
            f"decision_dedupe_applied={paper_trade_decision.get('decision_dedupe_applied', 0)}"
        ),
        (
            f"  paper_trade_decision_reason_codes="
            f"{','.join(paper_trade_decision.get('paper_trade_decision_reason_codes') or []) or 'none'}"
        ),
        f"  paper_trade_decision_examples={paper_trade_decision_examples or []}",
        'paper_trade_dispatch_summary:',
        (
            f"  route_expected={paper_trade_dispatch.get('route_expected', 0)} "
            f"dispatch_created={paper_trade_dispatch.get('dispatch_created', 0)} "
            f"dispatch_reused={paper_trade_dispatch.get('dispatch_reused', 0)} "
            f"dispatch_blocked={paper_trade_dispatch.get('dispatch_blocked', 0)} "
            f"dispatch_dedupe_applied={paper_trade_dispatch.get('dispatch_dedupe_applied', 0)}"
        ),
        (
            f"  paper_trade_dispatch_reason_codes="
            f"{','.join(paper_trade_dispatch.get('paper_trade_dispatch_reason_codes') or []) or 'none'}"
        ),
        f"  paper_trade_dispatch_examples={paper_trade_dispatch_examples or []}",
        'paper_trade_final_summary:',
        (
            f"  expected={paper_trade_final.get('expected', 0)} "
            f"available={paper_trade_final.get('available', 0)} "
            f"attempted={paper_trade_final.get('attempted', 0)} "
            f"created={paper_trade_final.get('created', 0)} "
            f"reused={paper_trade_final.get('reused', 0)} "
            f"blocked={paper_trade_final.get('blocked', 0)}"
        ),
        (
            f"  final_trade_reason_codes="
            f"{','.join(paper_trade_final.get('final_trade_reason_codes') or []) or 'none'}"
        ),
        f"  paper_trade_final_examples={paper_trade_final_examples or []}",
        'execution_candidate_creation_gate_summary:',
        (
            f"  candidates_suppressed_before_creation={execution_creation_gate.get('candidates_suppressed_before_creation', 0)} "
            f"candidates_created={execution_creation_gate.get('candidates_created', 0)} "
            f"candidates_allowed_for_exit={execution_creation_gate.get('candidates_allowed_for_exit', 0)} "
            f"candidates_allowed_without_exposure={execution_creation_gate.get('candidates_allowed_without_exposure', 0)}"
        ),
        (
            f"  execution_candidate_creation_gate_reason_codes="
            f"{','.join(execution_creation_gate.get('execution_candidate_creation_gate_reason_codes') or []) or 'none'}"
        ),
        (
            f"  measurement_scope={execution_creation_gate.get('measurement_scope') or 'pre_creation_execution_candidate_gate'} "
            f"source_of_truth={execution_creation_gate.get('source_of_truth') or 'execution_candidate_creation_bridge'} "
            f"explains_pre_creation_suppression={bool(execution_creation_gate.get('explains_pre_creation_suppression', True))}"
        ),
        f"  execution_candidate_creation_gate_examples={execution_creation_gate_examples or []}",
        'execution_exposure_provenance_summary:',
        (
            f"  suppressions_total={execution_exposure_provenance.get('suppressions_total', 0)} "
            f"exact_match_count={execution_exposure_provenance.get('exact_match_count', 0)} "
            f"weak_match_count={execution_exposure_provenance.get('weak_match_count', 0)} "
            f"stale_exposure_suspected_count={execution_exposure_provenance.get('stale_exposure_suspected_count', 0)} "
            f"additive_entries_suppressed={execution_exposure_provenance.get('additive_entries_suppressed', 0)} "
            f"reduce_or_exit_allowed={execution_exposure_provenance.get('reduce_or_exit_allowed', 0)}"
        ),
        (
            f"  suppressions_by_source_type={execution_exposure_provenance.get('suppressions_by_source_type') or {}} "
            f"suppressions_by_scope={execution_exposure_provenance.get('suppressions_by_scope') or {}}"
        ),
        (
            f"  dominant_exposure_reason_codes="
            f"{','.join(execution_exposure_provenance.get('dominant_exposure_reason_codes') or []) or 'none'}"
        ),
        f"  diagnostic_status={execution_exposure_provenance.get('diagnostic_status') or 'UNKNOWN'}",
        (
            "  provenance_summary=UNAVAILABLE"
            if bool(execution_exposure_provenance.get('diagnostic_unavailable'))
            else f"  provenance_summary={execution_exposure_provenance.get('provenance_summary') or ''}"
        ),
        f"  execution_exposure_provenance_examples={execution_exposure_provenance_examples or []}",
        'execution_exposure_release_audit_summary:',
        (
            f"  suppressions_audited={execution_exposure_release_audit.get('suppressions_audited', 0)} "
            f"valid_blockers_count={execution_exposure_release_audit.get('valid_blockers_count', 0)} "
            f"stale_suspected_count={execution_exposure_release_audit.get('stale_suspected_count', 0)} "
            f"terminal_but_still_matching_count={execution_exposure_release_audit.get('terminal_but_still_matching_count', 0)} "
            f"session_scope_mismatch_count={execution_exposure_release_audit.get('session_scope_mismatch_count', 0)} "
            f"mirror_lag_suspected_count={execution_exposure_release_audit.get('mirror_lag_suspected_count', 0)}"
        ),
        (
            f"  release_eligible_count={execution_exposure_release_audit.get('release_eligible_count', 0)} "
            f"release_pending_confirmation_count={execution_exposure_release_audit.get('release_pending_confirmation_count', 0)} "
            f"manual_review_required_count={execution_exposure_release_audit.get('manual_review_required_count', 0)} "
            f"keep_blocked_count={execution_exposure_release_audit.get('keep_blocked_count', 0)}"
        ),
        (
            f"  validity_reason_codes="
            f"{','.join(execution_exposure_release_audit.get('validity_reason_codes') or []) or 'none'} "
            f"release_reason_codes={','.join(execution_exposure_release_audit.get('release_reason_codes') or []) or 'none'}"
        ),
        f"  diagnostic_status={execution_exposure_release_audit.get('diagnostic_status') or 'UNKNOWN'}",
        (
            "  release_audit_summary=UNAVAILABLE"
            if bool(execution_exposure_release_audit.get('diagnostic_unavailable'))
            else f"  release_audit_summary={execution_exposure_release_audit.get('release_audit_summary') or ''}"
        ),
        f"  execution_exposure_release_audit_examples={execution_exposure_release_audit_examples or []}",
        'active_exposure_readiness_throttle_summary:',
        (
            f"  markets_throttled={active_exposure_readiness_throttle.get('markets_throttled', 0)} "
            f"additive_entries_throttled_before_readiness={active_exposure_readiness_throttle.get('additive_entries_throttled_before_readiness', 0)} "
            f"readiness_created_normally={active_exposure_readiness_throttle.get('readiness_created_normally', 0)} "
            f"candidates_preserved_for_exit={active_exposure_readiness_throttle.get('candidates_preserved_for_exit', 0)} "
            f"candidates_preserved_without_valid_blocker={active_exposure_readiness_throttle.get('candidates_preserved_without_valid_blocker', 0)}"
        ),
        (
            f"  throttle_reason_codes="
            f"{','.join(active_exposure_readiness_throttle.get('throttle_reason_codes') or []) or 'none'}"
        ),
        f"  throttle_summary={active_exposure_readiness_throttle.get('throttle_summary') or ''}",
        f"  active_exposure_readiness_throttle_examples={active_exposure_readiness_throttle_examples or []}",
        'execution_promotion_gate_summary:',
        (
            f"  candidates_visible={execution_promotion_gate.get('candidates_visible', 0)} "
            f"candidates_promoted_to_decision={execution_promotion_gate.get('candidates_promoted_to_decision', 0)} "
            f"candidates_suppressed_by_active_position={execution_promotion_gate.get('candidates_suppressed_by_active_position', 0)} "
            f"candidates_suppressed_by_existing_open_trade={execution_promotion_gate.get('candidates_suppressed_by_existing_open_trade', 0)} "
            f"candidates_allowed_for_exit={execution_promotion_gate.get('candidates_allowed_for_exit', 0)} "
            f"candidates_allowed_without_exposure={execution_promotion_gate.get('candidates_allowed_without_exposure', 0)}"
        ),
        (
            f"  execution_promotion_gate_reason_codes="
            f"{','.join(execution_promotion_gate.get('execution_promotion_gate_reason_codes') or []) or 'none'}"
        ),
        f"  execution_promotion_gate_examples={execution_promotion_gate_examples or []}",
        'execution_lineage_summary:',
        (
            f"  visible_execution_candidates={execution_lineage.get('visible_execution_candidates', 0)} "
            f"executable_candidates={execution_lineage.get('executable_candidates', 0)} "
            f"candidates_considered={execution_lineage.get('candidates_considered', 0)} "
            f"candidates_deduplicated={execution_lineage.get('candidates_deduplicated', 0)} "
            f"decisions_created={execution_lineage.get('decisions_created', 0)} "
            f"decisions_reused={execution_lineage.get('decisions_reused', 0)} "
            f"dispatches_considered={execution_lineage.get('dispatches_considered', 0)} "
            f"dispatches_deduplicated={execution_lineage.get('dispatches_deduplicated', 0)} "
            f"trades_materialized={execution_lineage.get('trades_materialized', 0)} "
            f"trades_reused={execution_lineage.get('trades_reused', 0)} "
            f"materialized_paper_trades={execution_lineage.get('materialized_paper_trades', 0)} "
            f"reused_trade_cycles={execution_lineage.get('reused_trade_cycles', 0)}"
        ),
        f"  fanout_reason_codes={','.join(execution_lineage.get('fanout_reason_codes') or []) or 'none'}",
        'final_fanout_summary:',
        (
            f"  final_lineage_count={final_fanout.get('final_lineage_count', 0)} "
            f"unique_market_lineages={final_fanout.get('unique_market_lineages', 0)} "
            f"duplicate_execution_candidates={final_fanout.get('duplicate_execution_candidates', 0)} "
            f"duplicate_dispatches={final_fanout.get('duplicate_dispatches', 0)} "
            f"duplicate_trades={final_fanout.get('duplicate_trades', 0)} "
            f"final_fanout_status={final_fanout.get('final_fanout_status') or 'UNKNOWN'}"
        ),
        f"  final_fanout_reason_codes={','.join(final_fanout.get('final_fanout_reason_codes') or []) or 'none'}",
        f"  final_fanout_examples={final_fanout_examples or []}",
        'cash_pressure_summary:',
        (
            f"  cash_available={cash_pressure.get('cash_available', 0)} "
            f"executable_candidates={cash_pressure.get('executable_candidates', 0)} "
            f"estimated_cash_required={cash_pressure.get('estimated_cash_required', 0)} "
            f"candidates_blocked_by_cash={cash_pressure.get('candidates_blocked_by_cash', 0)} "
            f"candidates_reused={cash_pressure.get('candidates_reused', 0)} "
            f"cash_pressure_status={cash_pressure.get('cash_pressure_status') or 'UNKNOWN'}"
        ),
        f"  cash_pressure_reason_codes={','.join(cash_pressure.get('cash_pressure_reason_codes') or []) or 'none'}",
        f"  cash_pressure_examples={cash_pressure_examples or []}",
        'position_exposure_summary:',
        (
            f"  open_positions_detected={position_exposure.get('open_positions_detected', 0)} "
            f"candidates_blocked_by_active_position={position_exposure.get('candidates_blocked_by_active_position', 0)} "
            f"candidates_allowed_for_exit={position_exposure.get('candidates_allowed_for_exit', 0)} "
            f"candidates_allowed_without_exposure={position_exposure.get('candidates_allowed_without_exposure', 0)}"
        ),
        (
            f"  position_exposure_reason_codes="
            f"{','.join(position_exposure.get('position_exposure_reason_codes') or []) or 'none'}"
        ),
        (
            f"  measurement_scope={position_exposure.get('measurement_scope') or 'final_trade_position_gate'} "
            f"source_of_truth={position_exposure.get('source_of_truth') or 'final_trade_position_gate_bridge_and_portfolio_context'} "
            f"explains_pre_creation_suppression={bool(position_exposure.get('explains_pre_creation_suppression', False))}"
        ),
        'execution_artifact_summary:',
        (
            f"  execution_readiness_available_count={execution_artifact.get('execution_readiness_available_count', 0)} "
            f"readiness_created={execution_artifact.get('readiness_created', 0)} "
            f"readiness_reused={execution_artifact.get('readiness_reused', 0)} "
            f"candidate_created={execution_artifact.get('candidate_created', 0)} "
            f"candidate_reused={execution_artifact.get('candidate_reused', 0)} "
            f"candidate_visible={execution_artifact.get('candidate_visible', 0)} "
            f"candidate_hidden={execution_artifact.get('candidate_hidden', 0)} "
            f"execution_artifact_blocked_count={execution_artifact.get('execution_artifact_blocked_count', 0)}"
        ),
        (
            f"  execution_artifact_reason_codes="
            f"{','.join(execution_artifact.get('execution_artifact_reason_codes') or []) or 'none'}"
        ),
        (
            f"  measurement_scope={execution_artifact.get('measurement_scope') or 'readiness_and_candidate_artifacts'} "
            f"source_of_truth={execution_artifact.get('source_of_truth') or 'autonomous_execution_readiness_and_intake_candidate'} "
            f"explains_pre_creation_suppression={bool(execution_artifact.get('explains_pre_creation_suppression', True))}"
        ),
        f"  execution_artifact_examples={execution_artifact_examples or []}",
        'shortlist_handoff_summary:',
        (
            f"  shortlisted_signals={shortlist_handoff.get('shortlisted_signals', 0)} "
            f"handoff_attempted={shortlist_handoff.get('handoff_attempted', 0)} "
            f"handoff_created={shortlist_handoff.get('handoff_created', 0)} "
            f"handoff_blocked={shortlist_handoff.get('handoff_blocked', 0)}"
        ),
        f"  shortlist_handoff_reason_codes={','.join(shortlist_handoff.get('shortlist_handoff_reason_codes') or []) or 'none'}",
        (
            f"  shortlist_handoff_examples="
            f"{shortlist_handoff.get('shortlist_handoff_examples') or []}"
        ),
        'downstream_route_summary:',
        (
            f"  route_expected={downstream_route.get('route_expected', 0)} "
            f"route_available={downstream_route.get('route_available', 0)} "
            f"route_missing={downstream_route.get('route_missing', 0)} "
            f"route_attempted={downstream_route.get('route_attempted', 0)} "
            f"route_created={downstream_route.get('route_created', 0)} "
            f"route_blocked={downstream_route.get('route_blocked', 0)}"
        ),
        f"  downstream_route_reason_codes={','.join(downstream_route.get('downstream_route_reason_codes') or []) or 'none'}",
        f"  downstream_route_examples={downstream_route_examples or []}",
        'market_link_summary:',
        (
            f"  shortlisted_signals={market_link.get('shortlisted_signals', 0)} "
            f"market_link_attempted={market_link.get('market_link_attempted', 0)} "
            f"market_link_resolved={market_link.get('market_link_resolved', 0)} "
            f"market_link_missing={market_link.get('market_link_missing', 0)} "
            f"market_link_ambiguous={market_link.get('market_link_ambiguous', 0)}"
        ),
        f"  market_link_reason_codes={','.join(market_link.get('market_link_reason_codes') or []) or 'none'}",
        f"  market_link_examples={market_link_examples or []}",
        (
            f"  consensus_alignment=consensus_reviews={consensus_alignment.get('consensus_reviews', 0)} "
            f"shortlist_aligned={consensus_alignment.get('shortlist_aligned_consensus_reviews', 0)} "
            f"aligned_with_shortlist={consensus_alignment.get('consensus_aligned_with_shortlist', True)}"
        ),
        'handoff_scoring_summary:',
        (
            f"  handoff_ready={handoff_scoring.get('handoff_ready', 0)} "
            f"handoff_deferred={handoff_scoring.get('handoff_deferred', 0)} "
            f"handoff_blocked={handoff_scoring.get('handoff_blocked', 0)} "
            f"ready_threshold={handoff_scoring.get('ready_threshold', '')}"
        ),
        f"  handoff_status_reason_codes={','.join(handoff_scoring.get('handoff_status_reason_codes') or []) or 'none'}",
        f"  deferred_reasons={','.join(handoff_scoring.get('deferred_reasons') or []) or 'none'}",
        f"  handoff_scoring_examples={handoff_scoring_examples or []}",
        'handoff_borderline_summary:',
        (
            f"  borderline_handoffs={handoff_borderline.get('borderline_handoffs', 0)} "
            f"borderline_promoted={handoff_borderline.get('borderline_promoted', 0)} "
            f"borderline_blocked={handoff_borderline.get('borderline_blocked', 0)} "
            f"ready_threshold={handoff_borderline.get('ready_threshold', '')} "
            f"borderline_band={handoff_borderline.get('borderline_band', '')}"
        ),
        f"  borderline_reason_codes={','.join(handoff_borderline.get('borderline_reason_codes') or []) or 'none'}",
        f"  handoff_borderline_examples={handoff_borderline_examples or []}",
        'handoff_structural_summary:',
        (
            f"  structural_pass={handoff_structural.get('structural_pass', 0)} "
            f"structural_blocked={handoff_structural.get('structural_blocked', 0)} "
            f"structural_weakness_count={handoff_structural.get('structural_weakness_count', 0)} "
            f"structural_pass_count={handoff_structural.get('structural_pass_count', 0)} "
            f"override_enabled={handoff_structural.get('override_enabled', 0)} "
            f"override_promoted={handoff_structural.get('override_promoted', 0)} "
            f"override_blocked={handoff_structural.get('override_blocked', 0)}"
        ),
        f"  structural_reason_codes={','.join(handoff_structural.get('structural_reason_codes') or []) or 'none'}",
        f"  structural_block_reason_codes={','.join(handoff_structural.get('structural_block_reason_codes') or []) or 'none'}",
        f"  structural_guardrail_summary={handoff_structural.get('structural_guardrail_summary') or ''}",
        f"  handoff_structural_examples={handoff_structural_examples or []}",
        'prediction_intake_summary:',
        (
            f"  handoff_candidates={prediction_intake.get('handoff_candidates', 0)} "
            f"prediction_intake_attempted={prediction_intake.get('prediction_intake_attempted', 0)} "
            f"prediction_intake_created={prediction_intake.get('prediction_intake_created', 0)} "
            f"prediction_intake_blocked={prediction_intake.get('prediction_intake_blocked', 0)} "
            f"prediction_intake_eligible_count={prediction_intake.get('prediction_intake_eligible_count', 0)} "
            f"prediction_intake_ineligible_count={prediction_intake.get('prediction_intake_ineligible_count', 0)} "
            f"prediction_intake_reused_count={prediction_intake.get('prediction_intake_reused_count', 0)} "
            f"prediction_intake_missing_fields={prediction_intake.get('prediction_intake_missing_fields', 0)} "
            f"prediction_intake_guardrail_blocked={prediction_intake.get('prediction_intake_guardrail_blocked', 0)}"
        ),
        f"  prediction_intake_reason_codes={','.join(prediction_intake.get('prediction_intake_reason_codes') or []) or 'none'}",
        f"  prediction_intake_guardrail_reason_codes={','.join(prediction_intake.get('prediction_intake_guardrail_reason_codes') or []) or 'none'}",
        f"  prediction_intake_filter_reason_codes={','.join(prediction_intake.get('prediction_intake_filter_reason_codes') or []) or 'none'}",
        f"  prediction_intake_guardrail_summary={prediction_intake.get('prediction_intake_guardrail_summary') or ''}",
        f"  prediction_intake_examples={prediction_intake_examples or []}",
        'prediction_visibility_summary:',
        (
            f"  intake_created={prediction_visibility.get('prediction_intake_created_count', 0)} "
            f"intake_reused={prediction_visibility.get('prediction_intake_reused_count', 0)} "
            f"candidates_visible={prediction_visibility.get('prediction_candidates_visible_count', 0)} "
            f"candidates_hidden={prediction_visibility.get('prediction_candidates_hidden_count', 0)}"
        ),
        f"  prediction_visibility_reason_codes={','.join(prediction_visibility.get('prediction_visibility_reason_codes') or []) or 'none'}",
        f"  prediction_visibility_examples={prediction_visibility_examples or []}",
        'prediction_artifact_summary:',
        (
            f"  artifact_expected={prediction_artifact.get('prediction_artifact_expected_count', 0)} "
            f"conviction_review_available={prediction_artifact.get('conviction_review_available_count', 0)} "
            f"conviction_review_created={prediction_artifact.get('conviction_review_created_count', 0)} "
            f"conviction_review_reused={prediction_artifact.get('conviction_review_reused_count', 0)} "
            f"risk_ready_handoff_available={prediction_artifact.get('risk_ready_handoff_available_count', 0)} "
            f"risk_ready_handoff_created={prediction_artifact.get('risk_ready_handoff_created_count', 0)} "
            f"risk_ready_handoff_reused={prediction_artifact.get('risk_ready_handoff_reused_count', 0)} "
            f"artifact_blocked={prediction_artifact.get('prediction_artifact_blocked_count', 0)}"
        ),
        f"  prediction_artifact_reason_codes={','.join(prediction_artifact.get('prediction_artifact_reason_codes') or []) or 'none'}",
        f"  prediction_artifact_summary={prediction_artifact.get('prediction_artifact_summary') or ''}",
        f"  prediction_artifact_examples={prediction_artifact_examples or []}",
        'prediction_risk_summary:',
        (
            f"  risk_route_expected={prediction_risk.get('risk_route_expected', 0)} "
            f"risk_route_available={prediction_risk.get('risk_route_available', 0)} "
            f"risk_route_attempted={prediction_risk.get('risk_route_attempted', 0)} "
            f"risk_route_created={prediction_risk.get('risk_route_created', 0)} "
            f"risk_route_blocked={prediction_risk.get('risk_route_blocked', 0)} "
            f"risk_route_missing_status_count={prediction_risk.get('risk_route_missing_status_count', 0)}"
        ),
        f"  risk_route_reason_codes={','.join(prediction_risk.get('risk_route_reason_codes') or []) or 'none'}",
        f"  risk_route_summary={prediction_risk.get('risk_route_summary') or ''}",
        f"  prediction_risk_examples={prediction_risk_examples or []}",
        'prediction_risk_caution_summary:',
        (
            f"  monitor_only_candidates={prediction_risk_caution.get('monitor_only_candidates', 0)} "
            f"risk_with_caution_eligible_count={prediction_risk_caution.get('risk_with_caution_eligible_count', 0)} "
            f"risk_with_caution_promoted_count={prediction_risk_caution.get('risk_with_caution_promoted_count', 0)} "
            f"risk_with_caution_blocked_count={prediction_risk_caution.get('risk_with_caution_blocked_count', 0)}"
        ),
        f"  risk_with_caution_reason_codes={','.join(prediction_risk_caution.get('risk_with_caution_reason_codes') or []) or 'none'}",
        f"  runtime_ready_threshold={prediction_risk_caution.get('runtime_ready_threshold') or ''}",
        f"  caution_band={prediction_risk_caution.get('caution_band') or ''}",
        f"  risk_with_caution_summary={prediction_risk_caution.get('risk_with_caution_summary') or ''}",
        f"  prediction_risk_caution_examples={prediction_risk_caution_examples or []}",
        'prediction_status_summary:',
        (
            f"  monitor_only={prediction_status.get('prediction_status_monitor_only_count', 0)} "
            f"ready_for_runtime={prediction_status.get('prediction_status_ready_for_runtime_count', 0)} "
            f"blocked={prediction_status.get('prediction_status_blocked_count', 0)}"
        ),
        f"  prediction_status_reason_codes={','.join(prediction_status.get('prediction_status_reason_codes') or []) or 'none'}",
        f"  runtime_ready_threshold={prediction_status.get('runtime_ready_threshold') or ''}",
        f"  status_rule_summary={prediction_status.get('status_rule_summary') or ''}",
        f"  prediction_status_examples={prediction_status_examples or []}",
        'scan_summary:',
        f"  summary_window={scan.get('summary_window') or 'latest_scan_run'}",
        f"  runs={scan.get('runs', 0)} rss_items={scan.get('rss_items', 0)} reddit_items={scan.get('reddit_items', 0)} x_items={scan.get('x_items', 0)}",
        f"  deduped_items={scan.get('deduped_items', 0)} clusters={scan.get('clusters', 0)} shortlisted_signals={scan.get('shortlisted_signals', 0)}",
        'portfolio_summary:',
        f"  cash={portfolio.get('cash')} equity={portfolio.get('equity')} realized_pnl={portfolio.get('realized_pnl')} unrealized_pnl={portfolio.get('unrealized_pnl')}",
        f"  open_positions={portfolio.get('open_positions')} recent_trades_count={portfolio.get('recent_trades_count')}",
        (
            f"  account_summary_status={portfolio.get('account_summary_status')} "
            f"account_summary_reason_codes={','.join(portfolio.get('account_summary_reason_codes') or []) or 'none'}"
        ),
        'portfolio_trade_reconciliation_summary:',
        (
            f"  portfolio_trade_reconciliation_status="
            f"{portfolio_trade_reconciliation.get('portfolio_trade_reconciliation_status') or 'UNKNOWN'} "
            f"trades_considered={portfolio_trade_reconciliation.get('trades_considered', 0)} "
            f"positions_considered={portfolio_trade_reconciliation.get('positions_considered', 0)}"
        ),
        (
            f"  portfolio_trade_reconciliation_reason_codes="
            f"{','.join(portfolio_trade_reconciliation.get('portfolio_trade_reconciliation_reason_codes') or []) or 'none'}"
        ),
        f"  pnl_considered={portfolio_trade_reconciliation.get('pnl_considered') or {}}",
        f"reason_codes: {', '.join(payload.get('reason_codes') or []) or 'none'}",
        f"blockers: {', '.join(blockers) or 'none'}",
        f"warnings: {len(warnings)}",
    ]
    for item in warnings:
        lines.append(f'  - {item}')
    lines.append(f'errors: {len(errors)}')
    for item in errors:
        lines.append(f'  - {item}')

    lines.append(f"next_action_hint: {payload.get('next_action_hint')}")
    lines.append(f"summary: {payload.get('summary')}")
    return '\n'.join(lines)


def start_test_console(*, preset_name: str | None = None) -> dict[str, Any]:
    target_preset = (preset_name or PRESET_NAME).strip() or PRESET_NAME
    now = timezone.now()
    payload: dict[str, Any] = {
        'timestamp': now,
        'started_at': now,
        'ended_at': None,
        'preset_name': target_preset,
        'test_status': TEST_STATUS_RUNNING,
        'current_phase': 'bootstrap',
        'trial_status': 'SKIPPED',
        'validation_status': 'UNKNOWN',
        'trend_status': 'UNKNOWN',
        'readiness_status': 'UNKNOWN',
        'gate_status': 'UNKNOWN',
        'extended_run_status': 'NOT_RUN',
        'session_active': False,
        'heartbeat_active': False,
        'current_session_status': 'UNKNOWN',
        'attention_mode': 'UNKNOWN',
        'funnel_status': 'UNKNOWN',
        'handoff_summary': {},
        'shortlist_handoff_summary': {},
        'downstream_route_summary': {},
        'consensus_alignment': {},
        'warnings': [],
        'errors': [],
        'blocker_summary': [],
        'reason_codes': [],
        'step_results': [],
        'next_action_hint': 'Running test console pipeline',
        'last_event': 'Test console run started',
    }
    _set_state(status=_augment_progress(payload))

    scan_run: SourceScanRun | None = None

    try:
        bootstrap_result = bootstrap_live_read_only_paper_session(preset_name=target_preset, auto_start_heartbeat=True, start_now=True)
        payload['step_results'].append({'phase': 'bootstrap', 'status': 'ok', 'result': bootstrap_result})
        payload['updated_at'] = timezone.now()
        payload['last_event'] = 'Bootstrap completed'
        payload['last_reason_code'] = str(bootstrap_result.get('bootstrap_action') or '')
        _set_state(status=_augment_progress(payload))
        if str(bootstrap_result.get('bootstrap_action')) in {'BLOCKED', 'FAILED'}:
            payload['warnings'].append(f"bootstrap action={bootstrap_result.get('bootstrap_action')}")

        payload['current_phase'] = 'scan'
        payload['updated_at'] = timezone.now()
        payload['last_event'] = 'Scan phase started'
        _set_state(status=_augment_progress(payload))
        try:
            scan_run = run_scan_agent(triggered_by='mission_control_test_console')
            payload['step_results'].append(
                {
                    'phase': 'scan',
                    'status': 'ok',
                    'result': {
                        'run_id': scan_run.id,
                        'signal_count': scan_run.signal_count,
                        'deduped_item_count': scan_run.deduped_item_count,
                        'clustered_count': scan_run.clustered_count,
                    },
                }
            )
            payload['updated_at'] = timezone.now()
            payload['last_event'] = 'Scan completed'
            if int(scan_run.signal_count or 0) <= 0:
                payload['warnings'].append('scan produced zero signals')
                payload['blocker_summary'].append('SCAN_ZERO_SIGNALS')
                payload['last_reason_code'] = 'SCAN_ZERO_SIGNALS'
        except Exception as exc:  # pragma: no cover
            payload['warnings'].append(f'scan skipped/failed: {exc}')
            payload['step_results'].append({'phase': 'scan', 'status': 'warning', 'result': {'error': str(exc)}})
            payload['updated_at'] = timezone.now()
            payload['last_event'] = 'Scan warning'
            payload['last_reason_code'] = 'SCAN_WARNING'
        _set_state(status=_augment_progress(payload))

        payload['current_phase'] = 'consensus_review'
        payload['updated_at'] = timezone.now()
        payload['last_event'] = 'Handoff phase started'
        _set_state(status=_augment_progress(payload))
        shortlisted_count = 0
        if scan_run:
            shortlisted_count = scan_run.signals.filter(status=NarrativeSignalStatus.SHORTLISTED).count()
        else:
            shortlisted_count = NarrativeSignal.objects.filter(status=NarrativeSignalStatus.SHORTLISTED).count()
        if shortlisted_count > 0:
            try:
                consensus = run_consensus_review(triggered_by='mission_control_test_console')
                payload['step_results'].append(
                    {
                        'phase': 'consensus_review',
                        'status': 'ok',
                        'result': {
                            'consensus_run_id': consensus.id,
                            'considered_signal_count': consensus.considered_signal_count,
                        },
                    }
                )
                payload['updated_at'] = timezone.now()
                payload['last_event'] = 'Consensus review completed'
            except Exception as exc:  # pragma: no cover
                payload['warnings'].append(f'consensus review failed: {exc}')
                payload['step_results'].append({'phase': 'consensus_review', 'status': 'warning', 'result': {'error': str(exc)}})
                payload['updated_at'] = timezone.now()
                payload['last_event'] = 'Consensus review warning'
                payload['last_reason_code'] = 'CONSENSUS_WARNING'
            _set_state(status=_augment_progress(payload))
            try:
                pursuit = run_pursuit_review(
                    triggered_by='mission_control_test_console',
                    market_limit=max(int(shortlisted_count), 1),
                )
                payload['step_results'].append(
                    {
                        'phase': 'pursuit_review',
                        'status': 'ok',
                        'result': {
                            'pursuit_run_id': pursuit.id,
                            'considered_market_count': pursuit.considered_market_count,
                            'prediction_ready_count': pursuit.prediction_ready_count,
                        },
                    }
                )
                payload['updated_at'] = timezone.now()
                payload['last_event'] = 'Pursuit review completed'
            except Exception as exc:  # pragma: no cover
                payload['warnings'].append(f'pursuit review failed: {exc}')
                payload['step_results'].append({'phase': 'pursuit_review', 'status': 'warning', 'result': {'error': str(exc)}})
                payload['updated_at'] = timezone.now()
                payload['last_event'] = 'Pursuit review warning'
                payload['last_reason_code'] = 'PURSUIT_WARNING'
            _set_state(status=_augment_progress(payload))
        else:
            payload['step_results'].append({'phase': 'consensus_review', 'status': 'skipped', 'result': {'reason': 'no_shortlisted_signals'}})
            payload['step_results'].append({'phase': 'pursuit_review', 'status': 'skipped', 'result': {'reason': 'no_shortlisted_signals'}})
            payload['updated_at'] = timezone.now()
            payload['last_event'] = 'Handoff skipped'
            payload['last_reason_code'] = 'NO_SHORTLISTED_SIGNALS'
            _set_state(status=_augment_progress(payload))

        payload['current_phase'] = 'trial'
        payload['updated_at'] = timezone.now()
        payload['last_event'] = 'Execution trial started'
        _set_state(status=_augment_progress(payload))
        trial = run_live_paper_trial_run(preset_name=target_preset, heartbeat_passes=1)
        payload['trial_status'] = str(trial.get('trial_status') or 'UNKNOWN')
        payload['step_results'].append({'phase': 'trial', 'status': 'ok', 'result': trial})
        payload['updated_at'] = timezone.now()
        payload['last_event'] = 'Execution trial completed'
        _set_state(status=_augment_progress(payload))

        payload['current_phase'] = 'validation'
        payload['updated_at'] = timezone.now()
        payload['last_event'] = 'Risk validation started'
        _set_state(status=_augment_progress(payload))
        validation = build_live_paper_validation_digest(preset_name=target_preset)
        payload['validation_status'] = str(validation.get('validation_status') or 'UNKNOWN')
        payload['step_results'].append({'phase': 'validation', 'status': 'ok', 'result': validation})
        payload['updated_at'] = timezone.now()
        payload['last_event'] = 'Risk validation completed'
        _set_state(status=_augment_progress(payload))

        payload['current_phase'] = 'trend'
        payload['updated_at'] = timezone.now()
        payload['last_event'] = 'Trend review started'
        _set_state(status=_augment_progress(payload))
        trend = build_live_paper_trial_trend_digest(limit=5, preset=target_preset)
        payload['trend_status'] = str(trend.get('trend_status') or 'UNKNOWN')
        payload['readiness_status'] = str(trend.get('readiness_status') or 'UNKNOWN')
        payload['step_results'].append({'phase': 'trend', 'status': 'ok', 'result': trend})
        payload['updated_at'] = timezone.now()
        payload['last_event'] = 'Trend review completed'
        _set_state(status=_augment_progress(payload))

        payload['current_phase'] = 'gate'
        payload['updated_at'] = timezone.now()
        payload['last_event'] = 'Gate evaluation started'
        _set_state(status=_augment_progress(payload))
        gate = build_extended_paper_run_gate(preset_name=target_preset)
        payload['gate_status'] = str(gate.get('gate_status') or 'UNKNOWN')
        payload['reason_codes'] = list(dict.fromkeys(gate.get('reason_codes') or []))
        payload['step_results'].append({'phase': 'gate', 'status': 'ok', 'result': gate})
        if payload['gate_status'] == 'BLOCK':
            payload['blocker_summary'].append('GATE_BLOCKED')
            payload['last_reason_code'] = 'GATE_BLOCKED'
        payload['updated_at'] = timezone.now()
        payload['last_event'] = 'Gate evaluation completed'
        _set_state(status=_augment_progress(payload))

        payload['current_phase'] = 'extended_run'
        payload['updated_at'] = timezone.now()
        payload['last_event'] = 'Extended run phase started'
        _set_state(status=_augment_progress(payload))
        if payload['gate_status'] in {GATE_ALLOW, GATE_ALLOW_WITH_CAUTION}:
            launch = launch_extended_paper_run(preset_name=target_preset)
            payload['extended_run_status'] = str(launch.get('launch_status') or 'UNKNOWN')
            payload['step_results'].append({'phase': 'extended_run', 'status': 'ok', 'result': launch})
            payload['last_event'] = 'Extended run launch completed'
        else:
            payload['extended_run_status'] = 'SKIPPED_GATE_BLOCKED'
            payload['step_results'].append({'phase': 'extended_run', 'status': 'skipped', 'result': {'reason': 'gate_blocked'}})
            payload['last_reason_code'] = 'GATE_BLOCKED'
            payload['last_event'] = 'Extended run skipped (gate blocked)'
        payload['updated_at'] = timezone.now()
        _set_state(status=_augment_progress(payload))

        payload['current_phase'] = 'finalize'
        payload['updated_at'] = timezone.now()
        payload['last_event'] = 'Finalizing test console run'
        _set_state(status=_augment_progress(payload))
        _sync_operational_snapshot(payload=payload, preset_name=target_preset, scan_run=scan_run)

        has_errors = bool(payload['errors'])
        has_warnings = bool(payload['warnings'] or payload['blocker_summary'])
        if has_errors:
            payload['test_status'] = TEST_STATUS_FAILED
        elif payload.get('gate_status') == 'BLOCK':
            payload['test_status'] = TEST_STATUS_BLOCKED
        elif has_warnings:
            payload['test_status'] = TEST_STATUS_COMPLETED_WITH_WARNINGS
        else:
            payload['test_status'] = TEST_STATUS_COMPLETED
    except Exception as exc:
        payload['errors'].append(str(exc))
        payload['test_status'] = TEST_STATUS_FAILED
        payload['updated_at'] = timezone.now()
        payload['last_event'] = 'Run failed'
    finally:
        payload['ended_at'] = timezone.now()
        payload['updated_at'] = timezone.now()
        overlay = payload.get('active_operational_overlay_summary') or {}
        payload['summary'] = (
            f"{payload['test_status']}: phase={payload.get('current_phase')} trial={payload.get('trial_status')} "
            f"validation={payload.get('validation_status')} gate={payload.get('gate_status')} "
            f"funnel_status={payload.get('funnel_status')} window_funnel_status={payload.get('funnel_status_window') or payload.get('funnel_status')} "
            f"overlay_status={overlay.get('overlay_status') or 'UNKNOWN'}"
        )
        payload['text_export'] = _log_line_items(payload)
        payload = _augment_progress(payload)
        _set_state(status=payload, log=payload, append_history=True)

    return payload


def stop_test_console(*, preset_name: str | None = None) -> dict[str, Any]:
    target_preset = (preset_name or PRESET_NAME).strip() or PRESET_NAME
    status_snapshot, _last_log, _history = _get_state_snapshot()

    runner_state = get_runner_state()
    runner_before = str(runner_state.runner_status)
    session = _find_active_preset_session(preset_name=target_preset)

    actions: list[str] = []
    warnings: list[str] = []

    if session and str(session.session_status) == AutonomousRuntimeSessionStatus.RUNNING:
        pause_session(session_id=session.id)
        actions.append(f'paused_session:{session.id}')
    elif session and str(session.session_status) == AutonomousRuntimeSessionStatus.PAUSED:
        actions.append(f'session_already_paused:{session.id}')
    else:
        warnings.append('no_reusable_autopilot_session_found')

    if runner_before == 'RUNNING':
        pause_runner()
        actions.append('paused_heartbeat_runner')
    else:
        warnings.append(f'heartbeat_not_running:{runner_before}')

    bootstrap_status = get_live_paper_bootstrap_status(preset_name=target_preset)
    stop_status = TEST_STATUS_STOPPED if actions else status_snapshot.get('test_status') or TEST_STATUS_IDLE

    payload = {
        **status_snapshot,
        'timestamp': timezone.now(),
        'preset_name': target_preset,
        'test_status': stop_status,
        'current_phase': 'finalize',
        'ended_at': timezone.now(),
        'session_active': bool(bootstrap_status.get('session_active')),
        'heartbeat_active': bool(bootstrap_status.get('heartbeat_active')),
        'current_session_status': str(bootstrap_status.get('current_session_status') or 'UNKNOWN'),
        'stop_actions': actions,
        'stop_warnings': warnings,
        'summary': (
            'Stop applied conservatively.' if actions else 'No explicit stop primitive was applied; reported current state only.'
        ),
        'next_action_hint': 'Run start again when ready for next V1 paper diagnostic cycle',
        'updated_at': timezone.now(),
        'last_event': 'Stop requested by operator',
        'last_reason_code': warnings[0] if warnings else (actions[0] if actions else None),
    }
    payload['text_export'] = _log_line_items(payload)
    payload = _augment_progress(payload)
    _set_state(status=payload, log=payload, append_history=True)
    return payload


def get_test_console_status() -> dict[str, Any]:
    status_snapshot, _last_log, _history = _get_state_snapshot()
    return _augment_progress(status_snapshot)


def export_test_console_log(*, fmt: str = 'text') -> dict[str, Any] | str:
    _status, last_log, history = _get_state_snapshot()
    payload = last_log or {
        'timestamp': timezone.now(),
        'test_status': TEST_STATUS_IDLE,
        'summary': 'No test has been executed yet.',
        'history_size': len(history),
    }
    if not payload.get('portfolio_trade_reconciliation_summary'):
        payload['portfolio_trade_reconciliation_summary'] = _build_portfolio_trade_reconciliation_summary(payload=payload)
    payload['reconciliation_status'] = str(payload['portfolio_trade_reconciliation_summary'].get('portfolio_trade_reconciliation_status') or 'UNKNOWN')
    payload['reconciliation_reason_codes'] = list(payload['portfolio_trade_reconciliation_summary'].get('portfolio_trade_reconciliation_reason_codes') or [])
    payload.setdefault('runtime_rejection_summary', str((payload.get('paper_trade_final_summary') or {}).get('runtime_rejection_summary') or ''))
    payload.setdefault('runtime_rejection_reason_codes', list((payload.get('paper_trade_final_summary') or {}).get('runtime_rejection_reason_codes') or []))
    if not payload.get('active_operational_overlay_summary'):
        overlay, effective_funnel_status, _overlay_text = _build_active_operational_overlay_summary(payload=payload)
        payload['active_operational_overlay_summary'] = overlay
        payload['funnel_status_window'] = str(payload.get('funnel_status_window') or payload.get('funnel_status') or 'UNKNOWN')
        payload['funnel_status'] = effective_funnel_status
    if not payload.get('llm_shadow_summary'):
        payload['llm_shadow_summary'] = build_llm_shadow_summary(payload=payload, funnel={})
    payload['latest_llm_shadow_summary'] = dict(payload.get('latest_llm_shadow_summary') or payload['llm_shadow_summary'].get('latest_llm_shadow_summary') or payload['llm_shadow_summary'])
    payload['llm_shadow_history_count'] = int(payload.get('llm_shadow_history_count') or payload['llm_shadow_summary'].get('llm_shadow_history_count') or 0)
    payload['llm_shadow_recent_history'] = list(payload.get('llm_shadow_recent_history') or payload['llm_shadow_summary'].get('llm_shadow_recent_history') or [])
    payload['llm_aux_signal_summary'] = build_llm_aux_signal_summary(payload=payload)
    exposure_diagnostics = normalize_execution_exposure_diagnostics(
        provenance_summary=payload.get('execution_exposure_provenance_summary'),
        provenance_examples=payload.get('execution_exposure_provenance_examples'),
        release_audit_summary=payload.get('execution_exposure_release_audit_summary'),
        release_audit_examples=payload.get('execution_exposure_release_audit_examples'),
    )
    payload['execution_exposure_provenance_summary'] = dict(exposure_diagnostics.get('execution_exposure_provenance_summary') or {})
    payload['execution_exposure_provenance_examples'] = list(exposure_diagnostics.get('execution_exposure_provenance_examples') or [])
    payload['execution_exposure_release_audit_summary'] = dict(exposure_diagnostics.get('execution_exposure_release_audit_summary') or {})
    payload['execution_exposure_release_audit_examples'] = list(exposure_diagnostics.get('execution_exposure_release_audit_examples') or [])
    if exposure_diagnostics.get('fallback_used'):
        payload['warnings'] = list(dict.fromkeys(list(payload.get('warnings') or []) + [TEST_CONSOLE_EXPORT_PARTIAL_DIAGNOSTIC_RECOVERED]))
        payload['reason_codes'] = list(dict.fromkeys(list(payload.get('reason_codes') or []) + [TEST_CONSOLE_EXPORT_PARTIAL_DIAGNOSTIC_RECOVERED]))
    if fmt == 'json':
        return payload
    return str(payload.get('text_export') or _log_line_items(payload))
