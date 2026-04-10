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
from apps.research_agent.models import NarrativeConsensusRecord
from apps.research_agent.models import MarketUniverseScanRun, NarrativeSignal, NarrativeSignalStatus, PredictionHandoffCandidate
from apps.research_agent.models import ResearchHandoffPriority, ResearchHandoffStatus, ResearchPursuitRun, ResearchStructuralAssessment
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


def _build_handoff_diagnostics(*, window_start) -> dict[str, Any]:
    shortlisted_qs = NarrativeSignal.objects.filter(
        status=NarrativeSignalStatus.SHORTLISTED,
        created_at__gte=window_start,
    )
    handoff_qs = PredictionHandoffCandidate.objects.filter(created_at__gte=window_start)
    consensus_qs = NarrativeConsensusRecord.objects.filter(created_at__gte=window_start)
    prediction_qs = PredictionConvictionReview.objects.filter(created_at__gte=window_start)
    risk_qs = RiskApprovalDecision.objects.filter(created_at__gte=window_start)
    paper_qs = AutonomousTradeCycleRun.objects.filter(started_at__gte=window_start)

    shortlisted_count = shortlisted_qs.count()
    handoff_count = handoff_qs.count()
    consensus_count = consensus_qs.count()
    prediction_count = prediction_qs.count()
    risk_count = risk_qs.count()
    paper_execution_count = paper_qs.count()

    shortlist_market_ids = {
        market_id
        for market_id in shortlisted_qs.values_list('linked_market_id', flat=True)
        if market_id is not None
    }
    shortlist_cluster_ids = {
        cluster_id
        for cluster_id in shortlisted_qs.values_list('linked_cluster_id', flat=True)
        if cluster_id is not None
    }
    handoff_market_ids = {
        market_id
        for market_id in handoff_qs.values_list('linked_market_id', flat=True)
        if market_id is not None
    }
    prediction_market_ids = {
        market_id
        for market_id in prediction_qs.values_list('linked_intake_candidate__linked_market_id', flat=True)
        if market_id is not None
    }
    risk_market_ids = {
        market_id
        for market_id in risk_qs.values_list('linked_candidate__linked_market_id', flat=True)
        if market_id is not None
    }

    handoff_reason_codes: list[str] = []
    stage_source_mismatch: dict[str, Any] = {}
    shortlist_handoff_summary = {
        'shortlisted_signals': int(shortlisted_count),
        'shortlisted_signal_ids': list(shortlisted_qs.values_list('id', flat=True)[:3]),
        'shortlisted_market_ids': sorted(list(shortlist_market_ids))[:3],
        'handoff_attempted': 0,
        'handoff_created': 0,
        'handoff_blocked': 0,
        'shortlist_handoff_reason_codes': [],
        'shortlist_handoff_examples': [],
        'summary': '',
    }

    recent_pursuit_run_count = ResearchPursuitRun.objects.filter(started_at__gte=window_start).count()
    assessed_market_ids = {
        market_id
        for market_id in ResearchStructuralAssessment.objects.filter(created_at__gte=window_start).values_list('linked_market_id', flat=True)
        if market_id is not None
    }
    priority_by_market: dict[int, str] = {}
    for market_id, status in ResearchHandoffPriority.objects.filter(
        created_at__gte=window_start,
        linked_market_id__in=list(shortlist_market_ids),
    ).values_list('linked_market_id', 'handoff_status'):
        if market_id is not None and market_id not in priority_by_market:
            priority_by_market[market_id] = status
    previous_handoff_market_ids = {
        market_id
        for market_id in PredictionHandoffCandidate.objects.filter(linked_market_id__in=list(shortlist_market_ids), created_at__lt=window_start).values_list(
            'linked_market_id', flat=True
        )
        if market_id is not None
    }

    shortlist_reason_codes: list[str] = []
    shortlist_examples: list[dict[str, Any]] = []
    attempted_count = 0
    created_count = 0
    blocked_count = 0
    shortlisted_rows = list(shortlisted_qs.values('id', 'linked_market_id')[:50])
    for row in shortlisted_rows:
        signal_id = int(row.get('id') or 0)
        market_id = row.get('linked_market_id')
        reason = 'SHORTLIST_BLOCKED_BY_FILTER'
        blocked = True
        attempted = False
        created = False

        if market_id is None:
            reason = 'SHORTLIST_BLOCKED_NO_MARKET_LINK'
        elif market_id in handoff_market_ids:
            reason = 'SHORTLIST_PROMOTED_TO_HANDOFF'
            attempted = True
            created = True
            blocked = False
        elif market_id in assessed_market_ids:
            reason = 'SHORTLIST_BLOCKED_BY_FILTER'
            attempted = True
        elif recent_pursuit_run_count == 0:
            reason = 'SHORTLIST_BLOCKED_NO_DOWNSTREAM_ROUTE'
        elif market_id in previous_handoff_market_ids:
            reason = 'SHORTLIST_BLOCKED_DUPLICATE_HANDOFF'
        elif priority_by_market.get(market_id) == ResearchHandoffStatus.WATCHLIST:
            reason = 'SHORTLIST_BLOCKED_LOW_PRIORITY'
        elif priority_by_market.get(market_id) == ResearchHandoffStatus.DEFERRED:
            reason = 'SHORTLIST_BLOCKED_CONSENSUS_REQUIRED'
        elif priority_by_market.get(market_id) == ResearchHandoffStatus.BLOCKED:
            reason = 'SHORTLIST_BLOCKED_BY_FILTER'
        elif priority_by_market.get(market_id) == ResearchHandoffStatus.READY_FOR_RESEARCH:
            reason = 'SHORTLIST_ELIGIBLE_FOR_HANDOFF'
        else:
            reason = 'SHORTLIST_BLOCKED_BY_FILTER'

        if attempted:
            attempted_count += 1
        if created:
            created_count += 1
        if blocked:
            blocked_count += 1
        shortlist_reason_codes.append(reason)
        if len(shortlist_examples) < 3:
            shortlist_examples.append({'signal_id': signal_id, 'market_id': market_id, 'reason_code': reason})

    shortlist_reason_codes = list(dict.fromkeys(shortlist_reason_codes))
    shortlist_handoff_summary = {
        **shortlist_handoff_summary,
        'handoff_attempted': int(attempted_count),
        'handoff_created': int(created_count),
        'handoff_blocked': int(blocked_count),
        'shortlist_handoff_reason_codes': shortlist_reason_codes,
        'shortlist_handoff_examples': shortlist_examples,
        'summary': (
            f"shortlisted_signals={shortlisted_count} handoff_attempted={attempted_count} handoff_created={created_count} "
            f"handoff_blocked={blocked_count} shortlist_handoff_reason_codes={','.join(shortlist_reason_codes) or 'none'}"
        ),
    }

    if shortlisted_count > 0 and handoff_count == 0:
        handoff_reason_codes.append('SHORTLIST_PRESENT_NO_HANDOFF')
    if handoff_count > 0:
        handoff_reason_codes.append('HANDOFF_CREATED')
    if handoff_count > 0 and consensus_count == 0:
        handoff_reason_codes.append('CONSENSUS_NOT_RUN')
    if consensus_count > 0 and handoff_count > 0 and prediction_count == 0:
        handoff_reason_codes.append('CONSENSUS_RAN_NO_PROMOTION')
    if handoff_count > 0 and prediction_count == 0:
        handoff_reason_codes.append('PREDICTION_STAGE_EMPTY')
    if prediction_count > 0 and risk_count == 0:
        handoff_reason_codes.append('RISK_STAGE_EMPTY')

    if shortlist_market_ids and handoff_market_ids:
        missing_from_handoff = sorted(shortlist_market_ids - handoff_market_ids)
        if missing_from_handoff:
            stage_source_mismatch['research_to_handoff_missing_market_ids'] = missing_from_handoff
    if handoff_market_ids and prediction_market_ids:
        missing_from_prediction = sorted(handoff_market_ids - prediction_market_ids)
        if missing_from_prediction:
            stage_source_mismatch['handoff_to_prediction_missing_market_ids'] = missing_from_prediction
    if prediction_market_ids and risk_market_ids:
        missing_from_risk = sorted(prediction_market_ids - risk_market_ids)
        if missing_from_risk:
            stage_source_mismatch['prediction_to_risk_missing_market_ids'] = missing_from_risk
    if stage_source_mismatch:
        handoff_reason_codes.append('FUNNEL_STAGE_SOURCE_MISMATCH')

    if shortlisted_count > 0 and prediction_count == 0 and risk_count == 0 and paper_execution_count == 0:
        handoff_reason_codes.append('DOWNSTREAM_EVIDENCE_INSUFFICIENT')

    aligned_consensus_count = 0
    if shortlist_cluster_ids:
        aligned_consensus_count = NarrativeConsensusRecord.objects.filter(
            created_at__gte=window_start,
            linked_cluster_id__in=list(shortlist_cluster_ids),
        ).count()
    if consensus_count > 0 and aligned_consensus_count == 0:
        handoff_reason_codes.append('CONSENSUS_DECOUPLED_FROM_SHORTLIST')
    consensus_alignment = {
        'consensus_reviews': int(consensus_count),
        'shortlist_aligned_consensus_reviews': int(aligned_consensus_count),
        'consensus_aligned_with_shortlist': bool(consensus_count == 0 or aligned_consensus_count > 0),
    }

    normalized_codes = list(dict.fromkeys(handoff_reason_codes))
    handoff_summary = (
        f"shortlisted_signals={shortlisted_count} handoff_candidates={handoff_count} "
        f"consensus_reviews={consensus_count} prediction_candidates={prediction_count} "
        f"risk_decisions={risk_count} paper_execution_candidates={paper_execution_count} "
        f"handoff_reason_codes={','.join(normalized_codes) or 'none'}"
    )

    return {
        'shortlisted_signals': int(shortlisted_count),
        'handoff_candidates': int(handoff_count),
        'consensus_reviews': int(consensus_count),
        'prediction_candidates': int(prediction_count),
        'risk_decisions': int(risk_count),
        'paper_execution_candidates': int(paper_execution_count),
        'handoff_reason_codes': normalized_codes,
        'stage_source_mismatch': stage_source_mismatch,
        'handoff_summary': handoff_summary,
        'shortlist_handoff_summary': shortlist_handoff_summary,
        'consensus_alignment': consensus_alignment,
    }


def _infer_stalled_reason_code(*, stalled_stage: str | None, handoff_diagnostics: dict[str, Any]) -> str | None:
    if not stalled_stage:
        return None
    if (
        stalled_stage == 'research'
        and 'SHORTLIST_PRESENT_NO_HANDOFF' in list(handoff_diagnostics.get('handoff_reason_codes') or [])
    ):
        return 'SHORTLIST_PRESENT_NO_HANDOFF'
    return f'{stalled_stage.upper()}_STAGE_EMPTY'


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
    risk_decision_count = counts.risk_approved_count + counts.risk_blocked_count
    handoff_diagnostics = _build_handoff_diagnostics(window_start=window_start)
    stalled_reason_code = _infer_stalled_reason_code(stalled_stage=stalled_stage, handoff_diagnostics=handoff_diagnostics)
    if not stalled_reason_code and stalled_stage:
        stage_reason_map = {
            'prediction': 'PREDICTION_STAGE_EMPTY',
            'risk': 'RISK_STAGE_EMPTY',
        }
        reason_candidate = stage_reason_map.get(stalled_stage)
        if reason_candidate and reason_candidate in handoff_diagnostics.get('handoff_reason_codes', []):
            stalled_reason_code = reason_candidate
        elif 'DOWNSTREAM_EVIDENCE_INSUFFICIENT' in handoff_diagnostics.get('handoff_reason_codes', []):
            stalled_reason_code = 'DOWNSTREAM_EVIDENCE_INSUFFICIENT'
    stalled_missing_counter = {
        'scan': 'scan_count',
        'research': 'research_count',
        'prediction': 'prediction_count',
        'risk': 'risk_decision_count',
        'paper_execution': 'paper_execution_count',
    }.get(stalled_stage or '')
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
        f'heartbeat_alive={heartbeat_alive}, validation={validation.get("validation_status")}, '
        f'handoff={handoff_diagnostics.get("handoff_summary")}.'
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
        'risk_decision_count': risk_decision_count,
        'paper_execution_count': counts.paper_execution_count,
        'recent_trades_count': counts.recent_trades_count,
        'top_stage': top_stage,
        'stalled_stage': stalled_stage,
        'stalled_reason_code': stalled_reason_code,
        'stalled_missing_counter': stalled_missing_counter,
        'handoff_reason_codes': handoff_diagnostics.get('handoff_reason_codes', []),
        'stage_source_mismatch': handoff_diagnostics.get('stage_source_mismatch', {}),
        'handoff_summary': handoff_diagnostics.get('handoff_summary', ''),
        'shortlist_handoff_summary': handoff_diagnostics.get('shortlist_handoff_summary', {}),
        'consensus_alignment': handoff_diagnostics.get('consensus_alignment', {}),
        'shortlisted_signals': handoff_diagnostics.get('shortlisted_signals', 0),
        'handoff_candidates': handoff_diagnostics.get('handoff_candidates', 0),
        'consensus_reviews': handoff_diagnostics.get('consensus_reviews', 0),
        'prediction_candidates': handoff_diagnostics.get('prediction_candidates', 0),
        'risk_decisions': handoff_diagnostics.get('risk_decisions', 0),
        'paper_execution_candidates': handoff_diagnostics.get('paper_execution_candidates', 0),
        'next_action_hint': next_action_hint,
        'funnel_summary': funnel_summary,
        'stages': stages,
    }
