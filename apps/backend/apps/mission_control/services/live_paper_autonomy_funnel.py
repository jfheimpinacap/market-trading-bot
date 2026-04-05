from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.db.models import Sum
from django.utils import timezone

from apps.autonomous_trader.models import AutonomousTradeCycleRun
from apps.mission_control.services.live_paper_bootstrap import PRESET_NAME
from apps.mission_control.services.live_paper_validation import build_live_paper_validation_digest
from apps.mission_control.services.session_heartbeat import build_heartbeat_summary
from apps.paper_trading.models import PaperTrade, PaperTradeStatus
from apps.paper_trading.services.portfolio import build_account_summary, get_active_account
from apps.prediction_agent.models import PredictionConvictionReview
from apps.research_agent.models import MarketUniverseScanRun, PredictionHandoffCandidate
from apps.risk_agent.models import RiskApprovalDecision

FUNNEL_ACTIVE = 'ACTIVE'
FUNNEL_THIN_FLOW = 'THIN_FLOW'
FUNNEL_STALLED = 'STALLED'

STAGE_ACTIVE = 'ACTIVE'
STAGE_LOW = 'LOW'
STAGE_EMPTY = 'EMPTY'

_LOW_THRESHOLD = 3


@dataclass(frozen=True)
class FunnelCounts:
    scan_count: int
    research_count: int
    prediction_count: int
    risk_approved_count: int
    risk_blocked_count: int
    paper_execution_count: int
    recent_trades_count: int


def _count_recent_trades_from_summary(*, window_start) -> int:
    account = get_active_account()
    summary = build_account_summary(account=account)
    recent_trades = summary.get('recent_trades') or []
    total = 0
    for trade in recent_trades:
        executed_at = trade.get('executed_at')
        if executed_at and executed_at >= window_start:
            total += 1
    return total


def _collect_funnel_counts(*, window_start) -> FunnelCounts:
    scan_count = MarketUniverseScanRun.objects.filter(started_at__gte=window_start).aggregate(
        total=Sum('markets_considered')
    ).get('total') or 0
    research_count = PredictionHandoffCandidate.objects.filter(created_at__gte=window_start).count()
    prediction_count = PredictionConvictionReview.objects.filter(created_at__gte=window_start).count()
    risk_approved_count = RiskApprovalDecision.objects.filter(
        created_at__gte=window_start,
        approval_status__in=['APPROVED', 'APPROVED_REDUCED'],
    ).count()
    risk_blocked_count = RiskApprovalDecision.objects.filter(
        created_at__gte=window_start,
        approval_status='BLOCKED',
    ).count()
    paper_execution_count = AutonomousTradeCycleRun.objects.filter(started_at__gte=window_start).aggregate(
        total=Sum('executed_paper_trade_count')
    ).get('total') or 0

    recent_trade_count = _count_recent_trades_from_summary(window_start=window_start)
    if recent_trade_count == 0:
        recent_trade_count = PaperTrade.objects.filter(
            status=PaperTradeStatus.EXECUTED,
            executed_at__gte=window_start,
        ).count()

    return FunnelCounts(
        scan_count=int(scan_count),
        research_count=int(research_count),
        prediction_count=int(prediction_count),
        risk_approved_count=int(risk_approved_count),
        risk_blocked_count=int(risk_blocked_count),
        paper_execution_count=int(paper_execution_count),
        recent_trades_count=int(recent_trade_count),
    )


def _stage_status(count: int) -> str:
    if count <= 0:
        return STAGE_EMPTY
    if count < _LOW_THRESHOLD:
        return STAGE_LOW
    return STAGE_ACTIVE


def _infer_status(*, counts: FunnelCounts) -> str:
    risk_total = counts.risk_approved_count + counts.risk_blocked_count
    stages_non_zero = sum(
        1 for value in [counts.scan_count, counts.research_count, counts.prediction_count, risk_total, counts.paper_execution_count] if value > 0
    )
    if stages_non_zero >= 3 and (risk_total > 0 or counts.paper_execution_count > 0):
        return FUNNEL_ACTIVE
    if counts.scan_count == 0 and counts.research_count == 0 and counts.prediction_count == 0 and risk_total == 0 and counts.paper_execution_count == 0:
        return FUNNEL_STALLED
    if counts.scan_count > 0 and counts.research_count == 0 and counts.prediction_count == 0 and risk_total == 0 and counts.paper_execution_count == 0:
        return FUNNEL_STALLED
    return FUNNEL_THIN_FLOW


def _infer_top_stage(*, counts: FunnelCounts) -> str:
    risk_total = counts.risk_approved_count + counts.risk_blocked_count
    ranked = [
        ('scan', counts.scan_count),
        ('research', counts.research_count),
        ('prediction', counts.prediction_count),
        ('risk', risk_total),
        ('paper_execution', counts.paper_execution_count),
    ]
    return max(ranked, key=lambda row: row[1])[0]


def _infer_stalled_stage(*, counts: FunnelCounts) -> str | None:
    risk_total = counts.risk_approved_count + counts.risk_blocked_count
    sequence = [
        ('scan', counts.scan_count),
        ('research', counts.research_count),
        ('prediction', counts.prediction_count),
        ('risk', risk_total),
        ('paper_execution', counts.paper_execution_count),
    ]
    for index in range(1, len(sequence)):
        previous = sequence[index - 1][1]
        current = sequence[index][1]
        if previous > 0 and current == 0:
            return sequence[index][0]
    return None


def _infer_hint(*, status: str, counts: FunnelCounts, stalled_stage: str | None) -> str:
    risk_total = counts.risk_approved_count + counts.risk_blocked_count
    if counts.risk_blocked_count > 0 and counts.risk_blocked_count >= max(counts.risk_approved_count, 1):
        return 'Risk is blocking most candidates'
    if status == FUNNEL_ACTIVE:
        return 'Autonomy funnel appears healthy'
    if counts.scan_count == 0:
        return 'No recent scan activity detected'
    if counts.prediction_count > 0 and risk_total == 0:
        return 'Flow is thin after prediction'
    if stalled_stage:
        return f'Flow is thin after {stalled_stage}'
    return 'Wait for another cycle and refresh'


def build_live_paper_autonomy_funnel_snapshot(*, window_minutes: int = 60, preset_name: str | None = None) -> dict[str, Any]:
    safe_window = max(5, min(int(window_minutes or 60), 24 * 60))
    target_preset = (preset_name or PRESET_NAME).strip() or PRESET_NAME
    window_start = timezone.now() - timedelta(minutes=safe_window)

    counts = _collect_funnel_counts(window_start=window_start)
    validation = build_live_paper_validation_digest(preset_name=target_preset)
    heartbeat_summary = build_heartbeat_summary()
    status = _infer_status(counts=counts)
    top_stage = _infer_top_stage(counts=counts)
    stalled_stage = _infer_stalled_stage(counts=counts)
    next_action_hint = _infer_hint(status=status, counts=counts, stalled_stage=stalled_stage)

    stages = [
        {
            'stage_name': 'scan',
            'count': counts.scan_count,
            'status': _stage_status(counts.scan_count),
            'summary': f'Scan observed {counts.scan_count} candidate signals in the last {safe_window}m.',
        },
        {
            'stage_name': 'research',
            'count': counts.research_count,
            'status': _stage_status(counts.research_count),
            'summary': f'Research pursued {counts.research_count} handoff candidates.',
        },
        {
            'stage_name': 'prediction',
            'count': counts.prediction_count,
            'status': _stage_status(counts.prediction_count),
            'summary': f'Prediction evaluated {counts.prediction_count} conviction reviews.',
        },
        {
            'stage_name': 'risk',
            'count': counts.risk_approved_count + counts.risk_blocked_count,
            'status': _stage_status(counts.risk_approved_count + counts.risk_blocked_count),
            'summary': f'Risk approved {counts.risk_approved_count} and blocked {counts.risk_blocked_count}.',
        },
        {
            'stage_name': 'paper_execution',
            'count': counts.paper_execution_count,
            'status': _stage_status(counts.paper_execution_count),
            'summary': f'Paper execution registered {counts.paper_execution_count} execution(s).',
        },
    ]

    heartbeat_alive = bool(heartbeat_summary.get('latest_run'))
    funnel_summary = (
        f'{status}: scan={counts.scan_count}, research={counts.research_count}, prediction={counts.prediction_count}, '
        f'risk_approved={counts.risk_approved_count}, risk_blocked={counts.risk_blocked_count}, '
        f'paper_execution={counts.paper_execution_count}, recent_trades={counts.recent_trades_count}, '
        f'heartbeat_alive={heartbeat_alive}, validation={validation.get("validation_status")}.'
    )

    return {
        'window_minutes': safe_window,
        'preset_name': target_preset,
        'funnel_status': status,
        'scan_count': counts.scan_count,
        'research_count': counts.research_count,
        'prediction_count': counts.prediction_count,
        'risk_approved_count': counts.risk_approved_count,
        'risk_blocked_count': counts.risk_blocked_count,
        'paper_execution_count': counts.paper_execution_count,
        'recent_trades_count': counts.recent_trades_count,
        'top_stage': top_stage,
        'stalled_stage': stalled_stage,
        'next_action_hint': next_action_hint,
        'funnel_summary': funnel_summary,
        'stages': stages,
    }
