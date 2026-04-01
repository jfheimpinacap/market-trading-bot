from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.prediction_agent.models import PredictionIntakeCandidate, PredictionIntakeRun, PredictionIntakeStatus
from apps.research_agent.models import PredictionHandoffCandidate, PredictionHandoffStatus


@dataclass
class IntakeResult:
    considered_count: int
    runtime_ready_count: int
    candidates: list[PredictionIntakeCandidate]


def _d(value: Decimal | None, default: str = '0.0000') -> Decimal:
    return Decimal(str(value if value is not None else default))


def build_intake_candidates(*, intake_run: PredictionIntakeRun, limit: int = 40) -> IntakeResult:
    handoffs = list(
        PredictionHandoffCandidate.objects.select_related(
            'linked_market',
            'linked_pursuit_score',
            'linked_consensus_record',
            'linked_divergence_record',
        )
        .order_by('-created_at', '-id')[:limit]
    )
    created: list[PredictionIntakeCandidate] = []
    runtime_ready_count = 0

    for handoff in handoffs:
        reason_codes = list(handoff.handoff_reason_codes or [])
        market_probability = handoff.linked_market.current_market_probability
        narrative_priority = _d(getattr(handoff.linked_consensus_record, 'confidence_score', None))
        structural_priority = _d(getattr(handoff.linked_pursuit_score, 'pursuit_score', None))
        handoff_confidence = _d(handoff.handoff_confidence)

        if market_probability is None:
            intake_status = PredictionIntakeStatus.BLOCKED
            reason_codes.append('BLOCKED_MISSING_MARKET_PROBABILITY')
        elif handoff.handoff_status == PredictionHandoffStatus.READY and handoff_confidence >= Decimal('0.5500'):
            intake_status = PredictionIntakeStatus.READY_FOR_RUNTIME
            runtime_ready_count += 1
            reason_codes.append('RUNTIME_READY_FROM_STRONG_RESEARCH_HANDOFF')
        elif handoff_confidence < Decimal('0.3500'):
            intake_status = PredictionIntakeStatus.INSUFFICIENT_CONTEXT
            reason_codes.append('LOW_HANDOFF_CONFIDENCE')
        else:
            intake_status = PredictionIntakeStatus.MONITOR_ONLY
            reason_codes.append('MONITOR_UNTIL_CONTEXT_IMPROVES')

        candidate = PredictionIntakeCandidate.objects.create(
            intake_run=intake_run,
            linked_market=handoff.linked_market,
            linked_prediction_handoff_candidate=handoff,
            linked_consensus_record=handoff.linked_consensus_record,
            linked_divergence_record=handoff.linked_divergence_record,
            linked_precedent_context={'source': 'memory_retrieval', 'enabled': True},
            linked_learning_context={'source': 'learning_memory', 'enabled': True},
            intake_status=intake_status,
            narrative_priority=narrative_priority,
            structural_priority=structural_priority,
            handoff_confidence=handoff_confidence,
            context_summary=handoff.handoff_summary,
            reason_codes=reason_codes,
            metadata={
                'handoff_status': handoff.handoff_status,
                'pursuit_priority_bucket': getattr(handoff.linked_pursuit_score, 'priority_bucket', ''),
            },
        )
        created.append(candidate)

    return IntakeResult(considered_count=len(handoffs), runtime_ready_count=runtime_ready_count, candidates=created)
