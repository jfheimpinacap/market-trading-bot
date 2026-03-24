from __future__ import annotations

from decimal import Decimal

from apps.evaluation_lab.models import EvaluationRun
from apps.learning_memory.models import LearningMemoryEntry, LearningMemoryType, LearningOutcome, LearningSourceType
from apps.postmortem_demo.models import TradeReview, TradeReviewOutcome
from apps.safety_guard.models import SafetyEvent


def _map_review_outcome(outcome: str) -> str:
    if outcome == TradeReviewOutcome.FAVORABLE:
        return LearningOutcome.POSITIVE
    if outcome == TradeReviewOutcome.UNFAVORABLE:
        return LearningOutcome.NEGATIVE
    return LearningOutcome.NEUTRAL


def _source_type_from_review(review: TradeReview) -> str:
    market_source = review.market.source_type
    if market_source == 'demo':
        return LearningSourceType.DEMO
    if market_source == 'real_read_only':
        return LearningSourceType.REAL_READ_ONLY
    return LearningSourceType.MIXED


def ingest_recent_reviews(*, lookback: int = 200) -> int:
    created = 0
    reviews = TradeReview.objects.select_related('paper_trade', 'market', 'market__provider').order_by('-reviewed_at', '-id')[:lookback]
    for review in reviews:
        defaults = {
            'memory_type': LearningMemoryType.TRADE_PATTERN,
            'source_type': _source_type_from_review(review),
            'provider': review.market.provider,
            'market': review.market,
            'related_trade': review.paper_trade,
            'outcome': _map_review_outcome(review.outcome),
            'score_delta': (review.score - Decimal('50.00')).quantize(Decimal('0.01')),
            'confidence_delta': (review.confidence - Decimal('0.50')).quantize(Decimal('0.0001')),
            'quantity_bias_delta': Decimal('-0.1000') if review.outcome == TradeReviewOutcome.UNFAVORABLE else Decimal('0.0000'),
            'summary': f'Review #{review.id}: {review.summary}',
            'rationale': review.lesson or review.rationale,
            'metadata': {
                'review_outcome': review.outcome,
                'review_status': review.review_status,
                'review_score': str(review.score),
                'review_confidence': str(review.confidence),
            },
        }
        _, was_created = LearningMemoryEntry.objects.update_or_create(
            related_review=review,
            defaults=defaults,
        )
        created += int(was_created)
    return created


def ingest_recent_evaluation_runs(*, lookback: int = 25) -> int:
    created = 0
    runs = EvaluationRun.objects.select_related('metric_set').order_by('-started_at', '-id')[:lookback]
    for run in runs:
        if not hasattr(run, 'metric_set'):
            continue
        metric_set = run.metric_set
        if metric_set.unfavorable_review_streak >= 2 or metric_set.blocked_count >= 3 or metric_set.safety_events_count >= 2:
            outcome = LearningOutcome.NEGATIVE
            confidence_delta = Decimal('-0.0600')
            quantity_delta = Decimal('-0.1200')
            summary = f'Evaluation run #{run.id} flagged conservative drift requirements.'
        elif metric_set.favorable_review_rate >= Decimal('0.60') and metric_set.block_rate <= Decimal('0.20'):
            outcome = LearningOutcome.POSITIVE
            confidence_delta = Decimal('0.0200')
            quantity_delta = Decimal('0.0000')
            summary = f'Evaluation run #{run.id} showed stable behavior under current guardrails.'
        else:
            outcome = LearningOutcome.NEUTRAL
            confidence_delta = Decimal('0.0000')
            quantity_delta = Decimal('0.0000')
            summary = f'Evaluation run #{run.id} produced neutral learning impact.'

        _, was_created = LearningMemoryEntry.objects.update_or_create(
            memory_type=LearningMemoryType.POLICY_PATTERN,
            related_review=None,
            summary=summary,
            defaults={
                'source_type': LearningSourceType.MIXED,
                'outcome': outcome,
                'score_delta': (metric_set.total_pnl / Decimal('20.00')).quantize(Decimal('0.01')),
                'confidence_delta': confidence_delta,
                'quantity_bias_delta': quantity_delta,
                'summary': summary,
                'rationale': 'Derived from evaluation metrics (streaks, safety events, block rate, and favorable rate).',
                'metadata': {
                    'run_id': run.id,
                    'market_scope': run.market_scope,
                    'blocked_count': metric_set.blocked_count,
                    'safety_events_count': metric_set.safety_events_count,
                    'unfavorable_review_streak': metric_set.unfavorable_review_streak,
                },
            },
        )
        created += int(was_created)
    return created


def ingest_recent_safety_events(*, lookback: int = 50) -> int:
    created = 0
    events = SafetyEvent.objects.order_by('-created_at', '-id')[:lookback]
    for event in events:
        if event.event_type not in {'KILL_SWITCH_TRIGGERED', 'HARD_STOP_TRIGGERED', 'COOLDOWN_TRIGGERED', 'APPROVAL_ESCALATION'}:
            continue
        summary = f'Safety event #{event.id} ({event.event_type}) suggests conservative bias.'
        _, was_created = LearningMemoryEntry.objects.update_or_create(
            memory_type=LearningMemoryType.POLICY_PATTERN,
            summary=summary,
            defaults={
                'source_type': LearningSourceType.MIXED,
                'outcome': LearningOutcome.NEGATIVE,
                'score_delta': Decimal('-8.00'),
                'confidence_delta': Decimal('-0.0400'),
                'quantity_bias_delta': Decimal('-0.0800'),
                'summary': summary,
                'rationale': event.message,
                'metadata': {
                    'safety_event_id': event.id,
                    'event_type': event.event_type,
                    'severity': event.severity,
                    'source': event.source,
                },
            },
        )
        created += int(was_created)
    return created
