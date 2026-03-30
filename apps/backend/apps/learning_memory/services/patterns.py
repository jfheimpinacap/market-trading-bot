from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.learning_memory.models import FailurePattern, FailurePatternStatus, FailurePatternType, LearningLoopScope
from apps.postmortem_agents.models import PostmortemBoardConclusion


PATTERN_MAP: dict[str, str] = {
    'narrative': FailurePatternType.NARRATIVE_MISS,
    'prediction': FailurePatternType.PREDICTION_OVERCONFIDENCE,
    'risk': FailurePatternType.RISK_SIZING_MISS,
    'runtime': FailurePatternType.RUNTIME_GUARD_MISS,
    'learning': FailurePatternType.PRECEDENT_IGNORED,
    'mixed': FailurePatternType.MULTI_FACTOR_FAILURE,
}


@dataclass
class DerivedPattern:
    pattern: FailurePattern
    created: bool


def _severity_to_score(severity: str) -> Decimal:
    if severity == 'high':
        return Decimal('0.85')
    if severity == 'medium':
        return Decimal('0.60')
    return Decimal('0.40')


def derive_patterns_from_postmortem(*, board_run_id: int | None = None) -> list[DerivedPattern]:
    conclusions = PostmortemBoardConclusion.objects.select_related('board_run', 'board_run__related_trade_review', 'board_run__related_trade_review__market')
    if board_run_id:
        conclusions = conclusions.filter(board_run_id=board_run_id)
    conclusions = conclusions.order_by('-created_at', '-id')[:100]

    derived: list[DerivedPattern] = []
    for conclusion in conclusions:
        market = conclusion.board_run.related_trade_review.market
        pattern_type = PATTERN_MAP.get(conclusion.primary_failure_mode, FailurePatternType.MULTI_FACTOR_FAILURE)
        canonical_label = f'{pattern_type}:{market.slug}'
        existing = FailurePattern.objects.filter(
            canonical_label=canonical_label,
            pattern_type=pattern_type,
            scope=LearningLoopScope.MARKET,
            scope_key=market.slug,
        ).first()

        recurrence = 1 if existing is None else existing.recurrence_count + 1
        severity_score = _severity_to_score(conclusion.severity)
        status = FailurePatternStatus.ACTIVE if recurrence >= 3 or severity_score >= Decimal('0.80') else FailurePatternStatus.WATCH
        reason_codes = ['POSTMORTEM_CONCLUSION', f'PRIMARY_MODE_{conclusion.primary_failure_mode.upper()}']

        defaults = {
            'severity_score': severity_score,
            'recurrence_count': recurrence,
            'evidence_summary': {
                'lesson_learned': conclusion.lesson_learned,
                'recommended_adjustments': conclusion.recommended_adjustments,
                'severity': conclusion.severity,
            },
            'linked_postmortems': sorted(list({*(existing.linked_postmortems if existing else []), conclusion.board_run_id})),
            'status': status,
            'rationale': conclusion.lesson_learned,
            'reason_codes': reason_codes,
            'metadata': {
                'market_slug': market.slug,
                'provider': market.provider.slug,
                'postmortem_conclusion_id': conclusion.id,
            },
        }
        pattern, created = FailurePattern.objects.update_or_create(
            canonical_label=canonical_label,
            pattern_type=pattern_type,
            scope=LearningLoopScope.MARKET,
            scope_key=market.slug,
            defaults=defaults,
        )
        derived.append(DerivedPattern(pattern=pattern, created=created))

    return derived
