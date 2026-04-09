from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from django.utils import timezone

from apps.autonomous_trader.models import AutonomousTradeCandidate
from apps.prediction_agent.models import PredictionConvictionReview
from apps.research_agent.models import NarrativeConsensusRun, NarrativeSignal, NarrativeSignalStatus, PredictionHandoffCandidate, SourceScanRun
from apps.risk_agent.models import RiskApprovalDecision

REASON_SHORTLIST_PRESENT_NO_HANDOFF = 'SHORTLIST_PRESENT_NO_HANDOFF'
REASON_HANDOFF_CREATED = 'HANDOFF_CREATED'
REASON_CONSENSUS_NOT_RUN = 'CONSENSUS_NOT_RUN'
REASON_CONSENSUS_RAN_NO_PROMOTION = 'CONSENSUS_RAN_NO_PROMOTION'
REASON_PREDICTION_STAGE_EMPTY = 'PREDICTION_STAGE_EMPTY'
REASON_RISK_STAGE_EMPTY = 'RISK_STAGE_EMPTY'
REASON_FUNNEL_STAGE_SOURCE_MISMATCH = 'FUNNEL_STAGE_SOURCE_MISMATCH'
REASON_DOWNSTREAM_EVIDENCE_INSUFFICIENT = 'DOWNSTREAM_EVIDENCE_INSUFFICIENT'


@dataclass(frozen=True)
class HandoffDiagnosticsCounts:
    shortlisted_signal_count: int
    handoff_candidate_count: int
    consensus_review_count: int
    prediction_candidate_count: int
    risk_decision_count: int
    paper_execution_candidate_count: int
    shortlist_market_ids: set[int]
    handoff_market_ids: set[int]


def _build_counts(*, window_start: datetime, scan_run: SourceScanRun | None = None) -> HandoffDiagnosticsCounts:
    shortlist_qs = NarrativeSignal.objects.filter(status=NarrativeSignalStatus.SHORTLISTED)
    if scan_run is not None:
        shortlist_qs = shortlist_qs.filter(scan_run=scan_run)
    else:
        shortlist_qs = shortlist_qs.filter(created_at_scan__gte=window_start)

    shortlisted_signal_count = shortlist_qs.count()
    shortlist_market_ids = {int(item) for item in shortlist_qs.exclude(linked_market_id__isnull=True).values_list('linked_market_id', flat=True)}

    handoff_qs = PredictionHandoffCandidate.objects.filter(created_at__gte=window_start)
    handoff_candidate_count = handoff_qs.count()
    handoff_market_ids = {int(item) for item in handoff_qs.exclude(linked_market_id__isnull=True).values_list('linked_market_id', flat=True)}

    return HandoffDiagnosticsCounts(
        shortlisted_signal_count=int(shortlisted_signal_count),
        handoff_candidate_count=int(handoff_candidate_count),
        consensus_review_count=int(NarrativeConsensusRun.objects.filter(started_at__gte=window_start).count()),
        prediction_candidate_count=int(PredictionConvictionReview.objects.filter(created_at__gte=window_start).count()),
        risk_decision_count=int(RiskApprovalDecision.objects.filter(created_at__gte=window_start).count()),
        paper_execution_candidate_count=int(AutonomousTradeCandidate.objects.filter(created_at__gte=window_start).count()),
        shortlist_market_ids=shortlist_market_ids,
        handoff_market_ids=handoff_market_ids,
    )


def build_handoff_diagnostics_from_counts(
    *,
    counts: HandoffDiagnosticsCounts,
    validation_status: str | None = None,
    gate_status: str | None = None,
    funnel_status: str | None = None,
) -> dict[str, Any]:
    reason_codes: list[str] = []

    if counts.shortlisted_signal_count > 0 and counts.handoff_candidate_count == 0:
        reason_codes.append(REASON_SHORTLIST_PRESENT_NO_HANDOFF)
    if counts.handoff_candidate_count > 0:
        reason_codes.append(REASON_HANDOFF_CREATED)

    if counts.shortlisted_signal_count > 0 and counts.consensus_review_count == 0:
        reason_codes.append(REASON_CONSENSUS_NOT_RUN)
    elif counts.shortlisted_signal_count > 0 and counts.consensus_review_count > 0 and counts.handoff_candidate_count == 0:
        reason_codes.append(REASON_CONSENSUS_RAN_NO_PROMOTION)

    if counts.handoff_candidate_count > 0 and counts.prediction_candidate_count == 0:
        reason_codes.append(REASON_PREDICTION_STAGE_EMPTY)

    if counts.prediction_candidate_count > 0 and counts.risk_decision_count == 0:
        reason_codes.append(REASON_RISK_STAGE_EMPTY)

    stage_source_mismatch = bool(
        counts.shortlist_market_ids
        and counts.handoff_market_ids
        and counts.shortlist_market_ids.isdisjoint(counts.handoff_market_ids)
    )
    if stage_source_mismatch:
        reason_codes.append(REASON_FUNNEL_STAGE_SOURCE_MISMATCH)

    downstream_gap = (
        counts.shortlisted_signal_count > 0
        and (counts.prediction_candidate_count == 0 or counts.risk_decision_count == 0)
        and str(validation_status or '').upper() in {'BLOCKED', 'WARNING'}
    ) or (
        counts.shortlisted_signal_count > 0
        and str(gate_status or '').upper() == 'BLOCK'
        and str(funnel_status or '').upper() == 'STALLED'
    )
    if downstream_gap:
        reason_codes.append(REASON_DOWNSTREAM_EVIDENCE_INSUFFICIENT)

    if counts.shortlisted_signal_count <= 0:
        bottleneck_stage = 'scan'
    elif counts.handoff_candidate_count <= 0:
        bottleneck_stage = 'research_handoff'
    elif counts.prediction_candidate_count <= 0:
        bottleneck_stage = 'prediction'
    elif counts.risk_decision_count <= 0:
        bottleneck_stage = 'risk'
    elif counts.paper_execution_candidate_count <= 0:
        bottleneck_stage = 'paper_execution'
    else:
        bottleneck_stage = 'none'

    handoff_summary = (
        f'bottleneck={bottleneck_stage}; shortlisted={counts.shortlisted_signal_count}; '
        f'handoff={counts.handoff_candidate_count}; consensus_runs={counts.consensus_review_count}; '
        f'prediction={counts.prediction_candidate_count}; risk={counts.risk_decision_count}; '
        f'paper_execution_candidates={counts.paper_execution_candidate_count}.'
    )

    return {
        'shortlisted_signals': counts.shortlisted_signal_count,
        'handoff_candidates': counts.handoff_candidate_count,
        'consensus_reviews': counts.consensus_review_count,
        'prediction_candidates': counts.prediction_candidate_count,
        'risk_decisions': counts.risk_decision_count,
        'paper_execution_candidates': counts.paper_execution_candidate_count,
        'stage_source_mismatch': stage_source_mismatch,
        'bottleneck_stage': bottleneck_stage,
        'handoff_reason_codes': list(dict.fromkeys(reason_codes)),
        'handoff_summary': handoff_summary,
    }


def build_live_paper_handoff_diagnostics(
    *,
    scan_run: SourceScanRun | None = None,
    window_minutes: int = 60,
    validation_status: str | None = None,
    gate_status: str | None = None,
    funnel_status: str | None = None,
) -> dict[str, Any]:
    safe_window = max(5, min(int(window_minutes or 60), 24 * 60))
    window_start = scan_run.started_at if scan_run is not None else timezone.now() - timedelta(minutes=safe_window)
    counts = _build_counts(window_start=window_start, scan_run=scan_run)
    return build_handoff_diagnostics_from_counts(
        counts=counts,
        validation_status=validation_status,
        gate_status=gate_status,
        funnel_status=funnel_status,
    )
