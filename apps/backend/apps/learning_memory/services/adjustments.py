from __future__ import annotations

from decimal import Decimal

from django.db.models import Avg, Count

from apps.learning_memory.models import LearningAdjustment, LearningAdjustmentType, LearningMemoryEntry, LearningOutcome, LearningScopeType


def _clamp_magnitude(magnitude: Decimal, max_adjustment_magnitude: Decimal) -> Decimal:
    floor = -abs(max_adjustment_magnitude)
    ceil = abs(max_adjustment_magnitude)
    return max(floor, min(ceil, magnitude)).quantize(Decimal('0.0001'))


def _upsert_adjustment(
    *,
    adjustment_type: str,
    scope_type: str,
    scope_key: str,
    magnitude: Decimal,
    reason: str,
    metadata: dict,
    max_adjustment_magnitude: Decimal,
) -> dict[str, int]:
    bounded_magnitude = _clamp_magnitude(magnitude, max_adjustment_magnitude)
    defaults = {
        'is_active': bounded_magnitude != Decimal('0.0000'),
        'magnitude': bounded_magnitude,
        'reason': reason,
        'metadata': metadata,
    }
    obj, created = LearningAdjustment.objects.update_or_create(
        adjustment_type=adjustment_type,
        scope_type=scope_type,
        scope_key=scope_key,
        defaults=defaults,
    )
    return {
        'created': int(created),
        'updated': int(not created),
        'deactivated': int((not obj.is_active) and bounded_magnitude == Decimal('0.0000')),
    }


def rebuild_active_adjustments(*, max_adjustment_magnitude: Decimal = Decimal('0.2000')) -> dict[str, int]:
    created_count = 0
    updated_count = 0
    deactivated_count = 0

    recent_ids = list(LearningMemoryEntry.objects.order_by('-created_at', '-id').values_list('id', flat=True)[:120])
    recent = LearningMemoryEntry.objects.filter(id__in=recent_ids)
    negatives = recent.filter(outcome=LearningOutcome.NEGATIVE).count()

    global_confidence_penalty = Decimal('-0.0400') if negatives >= 8 else Decimal('-0.0200') if negatives >= 4 else Decimal('0.0000')
    result = _upsert_adjustment(
        adjustment_type=LearningAdjustmentType.CONFIDENCE_BIAS,
        scope_type=LearningScopeType.GLOBAL,
        scope_key='global',
        magnitude=global_confidence_penalty,
        reason='Recent negative memory streak requires conservative confidence bias.' if global_confidence_penalty < 0 else 'No global confidence penalty needed.',
        metadata={'negative_recent_count': negatives},
        max_adjustment_magnitude=max_adjustment_magnitude,
    )
    created_count += result['created']
    updated_count += result['updated']
    deactivated_count += result['deactivated']

    source_groups = recent.values('source_type').annotate(total=Count('id'))
    for group in source_groups:
        source_type = group['source_type']
        total = group['total']
        negative_count = recent.filter(source_type=source_type, outcome=LearningOutcome.NEGATIVE).count()
        ratio = Decimal('0.0000') if total == 0 else (Decimal(negative_count) / Decimal(total)).quantize(Decimal('0.0001'))
        magnitude = Decimal('-0.1500') if ratio >= Decimal('0.50') and total >= 4 else Decimal('0.0000')
        result = _upsert_adjustment(
            adjustment_type=LearningAdjustmentType.QUANTITY_BIAS,
            scope_type=LearningScopeType.SOURCE_TYPE,
            scope_key=source_type,
            magnitude=magnitude,
            reason=f'Quantity bias for source_type={source_type} based on negative ratio {ratio}.',
            metadata={'negative_ratio': str(ratio), 'sample_size': total},
            max_adjustment_magnitude=max_adjustment_magnitude,
        )
        created_count += result['created']
        updated_count += result['updated']
        deactivated_count += result['deactivated']

    provider_groups = recent.exclude(provider=None).values('provider__slug').annotate(total=Count('id'))
    for group in provider_groups:
        provider_slug = group['provider__slug']
        total = group['total']
        negatives_provider = recent.filter(provider__slug=provider_slug, outcome=LearningOutcome.NEGATIVE).count()
        magnitude = Decimal('-0.1200') if total >= 3 and negatives_provider >= 2 else Decimal('0.0000')
        result = _upsert_adjustment(
            adjustment_type=LearningAdjustmentType.RISK_CAUTION_BIAS,
            scope_type=LearningScopeType.PROVIDER,
            scope_key=provider_slug,
            magnitude=magnitude,
            reason=f'Risk caution by provider={provider_slug} from recent negative outcomes.',
            metadata={'negative_count': negatives_provider, 'sample_size': total},
            max_adjustment_magnitude=max_adjustment_magnitude,
        )
        created_count += result['created']
        updated_count += result['updated']
        deactivated_count += result['deactivated']

    signal_groups = recent.exclude(related_signal=None).values('related_signal__signal_type').annotate(total=Count('id'), avg_conf=Avg('confidence_delta'))
    for group in signal_groups:
        signal_type = group['related_signal__signal_type']
        total = group['total']
        negatives_signal = recent.filter(related_signal__signal_type=signal_type, outcome=LearningOutcome.NEGATIVE).count()
        magnitude = Decimal('-0.0800') if total >= 2 and negatives_signal >= 2 else Decimal('0.0000')
        result = _upsert_adjustment(
            adjustment_type=LearningAdjustmentType.CONFIDENCE_BIAS,
            scope_type=LearningScopeType.SIGNAL_TYPE,
            scope_key=signal_type,
            magnitude=magnitude,
            reason=f'Signal-type confidence penalty for {signal_type} from negative outcomes.',
            metadata={'negative_count': negatives_signal, 'sample_size': total},
            max_adjustment_magnitude=max_adjustment_magnitude,
        )
        created_count += result['created']
        updated_count += result['updated']
        deactivated_count += result['deactivated']

    return {
        'memory_entries_processed': recent.count(),
        'adjustments_processed': created_count + updated_count,
        'adjustments_created': created_count,
        'adjustments_updated': updated_count,
        'adjustments_deactivated': deactivated_count,
    }
