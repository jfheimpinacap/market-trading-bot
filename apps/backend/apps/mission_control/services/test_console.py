from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from threading import Lock
from typing import Any

from django.utils import timezone

from apps.mission_control.models import AutonomousRuntimeSession, AutonomousRuntimeSessionStatus
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


def _set_state(*, status: dict[str, Any] | None = None, log: dict[str, Any] | None = None, append_history: bool = False) -> None:
    with _state_lock:
        if status is not None:
            _state.status = deepcopy(status)
        if log is not None:
            _state.last_log = deepcopy(log)
            if append_history:
                _state.history.appendleft(deepcopy(log))


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
    materialized = int(lineage.get('trades_materialized') or paper_trade_final.get('created') or 0)
    reused = int(lineage.get('trades_reused') or paper_trade_final.get('reused') or 0)
    recent_trades_count = int(portfolio.get('recent_trades_count') or 0)
    open_positions = int(portfolio.get('open_positions') or 0)
    equity = _to_float(portfolio.get('equity'))
    unrealized_pnl = _to_float(portfolio.get('unrealized_pnl'))
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
    if not reason_codes:
        reason_codes.append('PORTFOLIO_TRADE_RECONCILIATION_OK')
    status = 'OK'
    if any(code in reason_codes for code in ['PORTFOLIO_TRADE_COUNT_MISMATCH', 'PORTFOLIO_SCOPE_ALIGNMENT_MISMATCH']):
        status = 'CHECK'
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
        'trades_considered': int(materialized + reused),
        'positions_considered': int(open_positions),
        'pnl_considered': {'equity': equity, 'unrealized_pnl': unrealized_pnl},
        'reconciliation_summary': (
            f"materialized_paper_trades={materialized} reused_trade_cycles={reused} recent_trades_count={recent_trades_count} "
            f"open_positions={open_positions} equity={equity:.2f} unrealized_pnl={unrealized_pnl:.2f} "
            f"portfolio_trade_reconciliation_status={status} "
            f"portfolio_trade_reconciliation_reason_codes={','.join(normalized_codes) or 'none'}"
        ),
    }


def _sync_operational_snapshot(*, payload: dict[str, Any], preset_name: str, scan_run: SourceScanRun | None = None) -> None:
    bootstrap_status = get_live_paper_bootstrap_status(preset_name=preset_name)
    validation = build_live_paper_validation_digest(preset_name=preset_name)
    trend = build_live_paper_trial_trend_digest(limit=5, preset=preset_name)
    gate = build_extended_paper_run_gate(preset_name=preset_name)
    extended = get_extended_paper_run_status(preset_name=preset_name)
    attention = get_live_paper_attention_alert_status()
    funnel = build_live_paper_autonomy_funnel_snapshot(window_minutes=60, preset_name=preset_name)

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
                'route_expected': int(funnel.get('paper_execution_route_expected') or 0),
                'route_available': int(funnel.get('paper_execution_route_available') or 0),
                'route_attempted': int(funnel.get('paper_execution_route_attempted') or 0),
                'route_created': int(funnel.get('paper_execution_route_created') or 0),
                'route_reused': int(funnel.get('paper_execution_route_reused') or 0),
                'route_blocked': int(funnel.get('paper_execution_route_blocked') or 0),
                'route_missing_status_count': int(funnel.get('paper_execution_route_missing_status_count') or 0),
                'paper_execution_route_reason_codes': list(funnel.get('paper_execution_route_reason_codes') or []),
                'paper_execution_summary': str(funnel.get('paper_execution_summary') or ''),
            },
            'paper_execution_examples': list(funnel.get('paper_execution_examples') or []),
            'paper_execution_visibility_summary': {
                'created': int(funnel.get('paper_execution_created_count') or 0),
                'reused': int(funnel.get('paper_execution_reused_count') or 0),
                'visible': int(funnel.get('paper_execution_visible_count') or 0),
                'hidden': int(funnel.get('paper_execution_hidden_count') or 0),
                'paper_execution_visibility_reason_codes': list(funnel.get('paper_execution_visibility_reason_codes') or []),
                'paper_execution_visibility_summary': str(funnel.get('paper_execution_visibility_summary') or ''),
            },
            'paper_execution_visibility_examples': list(funnel.get('paper_execution_visibility_examples') or []),
            'paper_trade_summary': {
                'route_expected': int(funnel.get('paper_trade_route_expected') or 0),
                'route_available': int(funnel.get('paper_trade_route_available') or 0),
                'route_attempted': int(funnel.get('paper_trade_route_attempted') or 0),
                'route_created': int(funnel.get('paper_trade_route_created') or 0),
                'route_reused': int(funnel.get('paper_trade_route_reused') or 0),
                'route_blocked': int(funnel.get('paper_trade_route_blocked') or 0),
                'paper_trade_route_reason_codes': list(funnel.get('paper_trade_route_reason_codes') or []),
                'paper_trade_summary': str(funnel.get('paper_trade_summary') or ''),
            },
            'paper_trade_examples': list(funnel.get('paper_trade_examples') or []),
            'paper_trade_decision_summary': {
                'route_expected': int(funnel.get('paper_trade_route_expected') or 0),
                'decision_created': int(funnel.get('paper_trade_decision_created') or 0),
                'decision_reused': int(funnel.get('paper_trade_decision_reused') or 0),
                'decision_blocked': int(funnel.get('paper_trade_decision_blocked') or 0),
                'decision_dedupe_applied': int(funnel.get('paper_trade_decision_dedupe_applied') or 0),
                'paper_trade_decision_reason_codes': list(funnel.get('paper_trade_decision_reason_codes') or []),
                'paper_trade_decision_summary': str(funnel.get('paper_trade_decision_summary') or ''),
            },
            'paper_trade_decision_examples': list(funnel.get('paper_trade_decision_examples') or []),
            'paper_trade_dispatch_summary': {
                'route_expected': int(funnel.get('paper_trade_route_expected') or 0),
                'dispatch_created': int(funnel.get('paper_trade_dispatch_created') or 0),
                'dispatch_reused': int(funnel.get('paper_trade_dispatch_reused') or 0),
                'dispatch_blocked': int(funnel.get('paper_trade_dispatch_blocked') or 0),
                'dispatch_dedupe_applied': int(funnel.get('paper_trade_dispatch_dedupe_applied') or 0),
                'paper_trade_dispatch_reason_codes': list(funnel.get('paper_trade_dispatch_reason_codes') or []),
                'paper_trade_dispatch_summary': str(funnel.get('paper_trade_dispatch_summary') or ''),
            },
            'paper_trade_dispatch_examples': list(funnel.get('paper_trade_dispatch_examples') or []),
            'paper_trade_final_summary': {
                'expected': int(funnel.get('final_trade_expected') or 0),
                'available': int(funnel.get('final_trade_available') or 0),
                'attempted': int(funnel.get('final_trade_attempted') or 0),
                'created': int(funnel.get('final_trade_created') or 0),
                'reused': int(funnel.get('final_trade_reused') or 0),
                'blocked': int(funnel.get('final_trade_blocked') or 0),
                'final_trade_reason_codes': list(funnel.get('final_trade_reason_codes') or []),
                'paper_trade_final_summary': str(funnel.get('paper_trade_final_summary') or ''),
            },
            'paper_trade_final_examples': list(funnel.get('paper_trade_final_examples') or []),
            'execution_lineage_summary': dict(funnel.get('execution_lineage_summary') or {}),
            'final_fanout_summary': dict(funnel.get('final_fanout_summary') or {}),
            'final_fanout_examples': list(funnel.get('final_fanout_examples') or []),
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
            'reason_codes': list(dict.fromkeys(gate.get('reason_codes') or [])),
        }
    )
    payload['portfolio_trade_reconciliation_summary'] = _build_portfolio_trade_reconciliation_summary(payload=payload)
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
    execution_lineage = payload.get('execution_lineage_summary') or {}
    final_fanout = payload.get('final_fanout_summary') or {}
    final_fanout_examples = payload.get('final_fanout_examples') or []
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
    }
    _set_state(status=payload)

    scan_run: SourceScanRun | None = None

    try:
        bootstrap_result = bootstrap_live_read_only_paper_session(preset_name=target_preset, auto_start_heartbeat=True, start_now=True)
        payload['step_results'].append({'phase': 'bootstrap', 'status': 'ok', 'result': bootstrap_result})
        if str(bootstrap_result.get('bootstrap_action')) in {'BLOCKED', 'FAILED'}:
            payload['warnings'].append(f"bootstrap action={bootstrap_result.get('bootstrap_action')}")

        payload['current_phase'] = 'scan'
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
            if int(scan_run.signal_count or 0) <= 0:
                payload['warnings'].append('scan produced zero signals')
                payload['blocker_summary'].append('SCAN_ZERO_SIGNALS')
        except Exception as exc:  # pragma: no cover
            payload['warnings'].append(f'scan skipped/failed: {exc}')
            payload['step_results'].append({'phase': 'scan', 'status': 'warning', 'result': {'error': str(exc)}})

        payload['current_phase'] = 'consensus_review'
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
            except Exception as exc:  # pragma: no cover
                payload['warnings'].append(f'consensus review failed: {exc}')
                payload['step_results'].append({'phase': 'consensus_review', 'status': 'warning', 'result': {'error': str(exc)}})
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
            except Exception as exc:  # pragma: no cover
                payload['warnings'].append(f'pursuit review failed: {exc}')
                payload['step_results'].append({'phase': 'pursuit_review', 'status': 'warning', 'result': {'error': str(exc)}})
        else:
            payload['step_results'].append({'phase': 'consensus_review', 'status': 'skipped', 'result': {'reason': 'no_shortlisted_signals'}})
            payload['step_results'].append({'phase': 'pursuit_review', 'status': 'skipped', 'result': {'reason': 'no_shortlisted_signals'}})

        payload['current_phase'] = 'trial'
        trial = run_live_paper_trial_run(preset_name=target_preset, heartbeat_passes=1)
        payload['trial_status'] = str(trial.get('trial_status') or 'UNKNOWN')
        payload['step_results'].append({'phase': 'trial', 'status': 'ok', 'result': trial})

        payload['current_phase'] = 'validation'
        validation = build_live_paper_validation_digest(preset_name=target_preset)
        payload['validation_status'] = str(validation.get('validation_status') or 'UNKNOWN')
        payload['step_results'].append({'phase': 'validation', 'status': 'ok', 'result': validation})

        payload['current_phase'] = 'trend'
        trend = build_live_paper_trial_trend_digest(limit=5, preset=target_preset)
        payload['trend_status'] = str(trend.get('trend_status') or 'UNKNOWN')
        payload['readiness_status'] = str(trend.get('readiness_status') or 'UNKNOWN')
        payload['step_results'].append({'phase': 'trend', 'status': 'ok', 'result': trend})

        payload['current_phase'] = 'gate'
        gate = build_extended_paper_run_gate(preset_name=target_preset)
        payload['gate_status'] = str(gate.get('gate_status') or 'UNKNOWN')
        payload['reason_codes'] = list(dict.fromkeys(gate.get('reason_codes') or []))
        payload['step_results'].append({'phase': 'gate', 'status': 'ok', 'result': gate})
        if payload['gate_status'] == 'BLOCK':
            payload['blocker_summary'].append('GATE_BLOCKED')

        payload['current_phase'] = 'extended_run'
        if payload['gate_status'] in {GATE_ALLOW, GATE_ALLOW_WITH_CAUTION}:
            launch = launch_extended_paper_run(preset_name=target_preset)
            payload['extended_run_status'] = str(launch.get('launch_status') or 'UNKNOWN')
            payload['step_results'].append({'phase': 'extended_run', 'status': 'ok', 'result': launch})
        else:
            payload['extended_run_status'] = 'SKIPPED_GATE_BLOCKED'
            payload['step_results'].append({'phase': 'extended_run', 'status': 'skipped', 'result': {'reason': 'gate_blocked'}})

        payload['current_phase'] = 'finalize'
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
    finally:
        payload['ended_at'] = timezone.now()
        payload['summary'] = (
            f"{payload['test_status']}: phase={payload.get('current_phase')} trial={payload.get('trial_status')} "
            f"validation={payload.get('validation_status')} gate={payload.get('gate_status')}"
        )
        payload['text_export'] = _log_line_items(payload)
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
    }
    payload['text_export'] = _log_line_items(payload)
    _set_state(status=payload, log=payload, append_history=True)
    return payload


def get_test_console_status() -> dict[str, Any]:
    status_snapshot, _last_log, _history = _get_state_snapshot()
    return status_snapshot


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
    if fmt == 'json':
        return payload
    return str(payload.get('text_export') or _log_line_items(payload))
