from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.learning_memory.models import (
    FailurePattern,
    FailurePatternStatus,
    LoopAdjustmentStatus,
    LoopAdjustmentType,
    PostmortemLearningAdjustment,
)


TYPE_MAP: dict[str, str] = {
    'prediction_overconfidence': LoopAdjustmentType.CONFIDENCE_PENALTY,
    'weak_edge': LoopAdjustmentType.EDGE_PENALTY,
    'low_liquidity_trap': LoopAdjustmentType.LIQUIDITY_PENALTY,
    'risk_sizing_miss': LoopAdjustmentType.RISK_SIZE_CAP,
    'runtime_guard_miss': LoopAdjustmentType.WATCH_ESCALATION,
    'precedent_ignored': LoopAdjustmentType.MANUAL_REVIEW_TRIGGER,
}


@dataclass
class AdjustmentResult:
    adjustment: PostmortemLearningAdjustment
    created: bool


def derive_adjustments_from_patterns(*, patterns: list[FailurePattern]) -> list[AdjustmentResult]:
    results: list[AdjustmentResult] = []
    now = timezone.now()
    for pattern in patterns:
        adjustment_type = TYPE_MAP.get(pattern.pattern_type, LoopAdjustmentType.CATEGORY_CAUTION)
        status = LoopAdjustmentStatus.ACTIVE if pattern.status == FailurePatternStatus.ACTIVE else LoopAdjustmentStatus.PROPOSED
        if pattern.status == FailurePatternStatus.EXPIRED:
            status = LoopAdjustmentStatus.EXPIRED

        strength = min(Decimal('0.3000'), (Decimal(pattern.recurrence_count) * Decimal('0.0400')) + (pattern.severity_score * Decimal('0.0800')))
        if status == LoopAdjustmentStatus.PROPOSED:
            strength = min(strength, Decimal('0.1200'))

        adjustment, created = PostmortemLearningAdjustment.objects.update_or_create(
            linked_failure_pattern=pattern,
            adjustment_type=adjustment_type,
            scope=pattern.scope,
            scope_key=pattern.scope_key,
            defaults={
                'linked_postmortem_id': (pattern.linked_postmortems[-1] if pattern.linked_postmortems else None),
                'adjustment_strength': strength.quantize(Decimal('0.0001')),
                'status': status,
                'expiration_hint': now + timedelta(days=14),
                'rationale': f'Adjustment derived from failure pattern {pattern.canonical_label}.',
                'reason_codes': pattern.reason_codes,
                'metadata': {
                    'recurrence_count': pattern.recurrence_count,
                    'severity_score': str(pattern.severity_score),
                },
            },
        )
        results.append(AdjustmentResult(adjustment=adjustment, created=created))

    stale_cutoff = now - timedelta(days=14)
    PostmortemLearningAdjustment.objects.filter(status=LoopAdjustmentStatus.ACTIVE, updated_at__lt=stale_cutoff).update(status=LoopAdjustmentStatus.EXPIRED)
    return results
