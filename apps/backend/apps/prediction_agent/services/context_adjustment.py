from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.memory_retrieval.services.assist import run_assist
from apps.memory_retrieval.models import MemoryQueryType
from apps.prediction_agent.services.calibration import clamp_probability, q4


@dataclass
class ContextAdjustmentResult:
    adjusted_edge: Decimal
    precedent_caution_score: Decimal
    narrative_influence_score: Decimal
    signal_conflict_score: Decimal
    reason_codes: list[str]
    metadata: dict


def apply_context_adjustment(*, market_id: int, market_probability: Decimal, calibrated_probability: Decimal, narrative_support_score: Decimal, divergence_score: Decimal) -> ContextAdjustmentResult:
    reason_codes: list[str] = []
    precedent_caution = Decimal('0.0000')
    precedent_summary: dict = {}

    try:
        assist_run = run_assist(
            query_text=f'market:{market_id} prediction caution precedents',
            query_type=MemoryQueryType.PREDICTION,
            context_metadata={'market_id': market_id, 'source': 'prediction_runtime_review'},
            limit=4,
        )
        precedent_summary = assist_run.summary or {}
        if assist_run.retrieval_run.result_count > 0:
            precedent_caution = min(Decimal('0.4000'), Decimal(str(assist_run.precedent_confidence)) * Decimal('0.45'))
            reason_codes.append('PRECEDENT_CONTEXT_FOUND')
    except Exception:
        reason_codes.append('PRECEDENT_CONTEXT_UNAVAILABLE')

    narrative_influence = (narrative_support_score - Decimal('0.5000')) * Decimal('0.1200')
    narrative_influence = q4(max(Decimal('-0.0800'), min(Decimal('0.0800'), narrative_influence)))

    signal_conflict = Decimal('0.0000')
    if divergence_score >= Decimal('0.5000'):
        signal_conflict = min(Decimal('0.7000'), divergence_score)
        reason_codes.append('HIGH_SIGNAL_DIVERGENCE')

    raw_edge = calibrated_probability - market_probability
    adjusted_edge = raw_edge + narrative_influence - (precedent_caution * Decimal('0.30'))
    adjusted_edge = q4(max(Decimal('-0.9900'), min(Decimal('0.9900'), adjusted_edge)))

    return ContextAdjustmentResult(
        adjusted_edge=adjusted_edge,
        precedent_caution_score=clamp_probability(q4(precedent_caution)),
        narrative_influence_score=q4(narrative_influence),
        signal_conflict_score=clamp_probability(q4(signal_conflict)),
        reason_codes=reason_codes,
        metadata={'precedent_summary': precedent_summary},
    )
