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


RUNTIME_READY_CONFIDENCE_THRESHOLD = Decimal('0.5500')
RUNTIME_READY_WITH_CAUTION_CONFIDENCE_THRESHOLD = Decimal('0.5000')
RUNTIME_READY_WITH_CAUTION_NARRATIVE_THRESHOLD = Decimal('0.6500')
RUNTIME_READY_WITH_CAUTION_STRUCTURAL_THRESHOLD = Decimal('0.7000')
RUNTIME_READY_WITH_CAUTION_STRUCTURAL_STRONG_THRESHOLD = Decimal('0.8000')
LOW_CONFIDENCE_THRESHOLD = Decimal('0.3500')


def derive_prediction_intake_status(
    *,
    handoff: PredictionHandoffCandidate,
    narrative_priority: Decimal,
    structural_priority: Decimal,
    handoff_confidence: Decimal,
) -> tuple[str, list[str], dict[str, str]]:
    status_reason_codes: list[str] = []
    diagnostics = {
        'handler': 'prediction_intake',
        'runtime_ready_confidence_threshold': str(RUNTIME_READY_CONFIDENCE_THRESHOLD),
        'runtime_ready_with_caution_threshold': (
            f"confidence>={RUNTIME_READY_WITH_CAUTION_CONFIDENCE_THRESHOLD},"
            f"structural>={RUNTIME_READY_WITH_CAUTION_STRUCTURAL_THRESHOLD},"
            f"(narrative>={RUNTIME_READY_WITH_CAUTION_NARRATIVE_THRESHOLD}"
            f"or structural>={RUNTIME_READY_WITH_CAUTION_STRUCTURAL_STRONG_THRESHOLD})"
        ),
        'low_confidence_threshold': str(LOW_CONFIDENCE_THRESHOLD),
    }

    if handoff.linked_market.current_market_probability is None:
        return PredictionIntakeStatus.BLOCKED, ['PREDICTION_STATUS_BLOCKED_BY_RULE'], diagnostics

    if handoff.handoff_status == PredictionHandoffStatus.READY and handoff_confidence >= RUNTIME_READY_CONFIDENCE_THRESHOLD:
        return PredictionIntakeStatus.READY_FOR_RUNTIME, ['PREDICTION_STATUS_READY_FOR_RUNTIME'], diagnostics

    if (
        handoff.handoff_status == PredictionHandoffStatus.READY
        and handoff_confidence >= RUNTIME_READY_WITH_CAUTION_CONFIDENCE_THRESHOLD
        and structural_priority >= RUNTIME_READY_WITH_CAUTION_STRUCTURAL_THRESHOLD
        and (
            narrative_priority >= RUNTIME_READY_WITH_CAUTION_NARRATIVE_THRESHOLD
            or structural_priority >= RUNTIME_READY_WITH_CAUTION_STRUCTURAL_STRONG_THRESHOLD
        )
    ):
        return PredictionIntakeStatus.READY_FOR_RUNTIME, ['PREDICTION_STATUS_READY_WITH_CAUTION'], diagnostics

    if handoff_confidence < LOW_CONFIDENCE_THRESHOLD:
        return PredictionIntakeStatus.INSUFFICIENT_CONTEXT, ['PREDICTION_STATUS_NOT_RUNTIME_READY'], diagnostics

    status_reason_codes.append('PREDICTION_STATUS_MONITOR_ONLY_LOW_CONFIDENCE')
    return PredictionIntakeStatus.MONITOR_ONLY, status_reason_codes, diagnostics


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

        intake_status, status_reason_codes, status_diagnostics = derive_prediction_intake_status(
            handoff=handoff,
            narrative_priority=narrative_priority,
            structural_priority=structural_priority,
            handoff_confidence=handoff_confidence,
        )
        if market_probability is None:
            reason_codes.append('BLOCKED_MISSING_MARKET_PROBABILITY')
        elif 'PREDICTION_STATUS_READY_FOR_RUNTIME' in status_reason_codes:
            runtime_ready_count += 1
            reason_codes.append('RUNTIME_READY_FROM_STRONG_RESEARCH_HANDOFF')
        elif 'PREDICTION_STATUS_READY_WITH_CAUTION' in status_reason_codes:
            runtime_ready_count += 1
            reason_codes.append('RUNTIME_READY_WITH_CAUTION_FROM_RESEARCH_HANDOFF')
        elif 'PREDICTION_STATUS_NOT_RUNTIME_READY' in status_reason_codes:
            reason_codes.append('LOW_HANDOFF_CONFIDENCE')
        else:
            reason_codes.append('MONITOR_UNTIL_CONTEXT_IMPROVES')
        reason_codes.extend(status_reason_codes)

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
                'prediction_intake_status_diagnostics': status_diagnostics,
            },
        )
        created.append(candidate)

    return IntakeResult(considered_count=len(handoffs), runtime_ready_count=runtime_ready_count, candidates=created)
