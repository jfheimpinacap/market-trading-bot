from dataclasses import dataclass
from decimal import Decimal


@dataclass
class ComputedMetrics:
    values: dict
    guidance: list[str]


def safe_rate(numerator: int, denominator: int) -> Decimal:
    if denominator <= 0:
        return Decimal('0')
    return (Decimal(numerator) / Decimal(denominator)).quantize(Decimal('0.0001'))


def build_guidance(metrics: dict) -> list[str]:
    guidance: list[str] = []
    block_rate = Decimal(metrics.get('block_rate', 0))
    auto_rate = Decimal(metrics.get('auto_execution_rate', 0))
    favorable_rate = Decimal(metrics.get('favorable_review_rate', 0))
    safety_events = int(metrics.get('safety_events_count', 0))
    pnl = Decimal(metrics.get('total_pnl', 0))

    if block_rate >= Decimal('0.40'):
        guidance.append('High block rate: system may be too conservative or proposal quality is low.')
    if auto_rate <= Decimal('0.15') and int(metrics.get('proposals_generated', 0)) >= 5:
        guidance.append('Low auto-execution rate: system may be under-trading relative to generated opportunities.')
    if favorable_rate < Decimal('0.50') and int(metrics.get('reviews_generated_count', 0)) >= 4:
        guidance.append('Review quality deteriorating: favorable reviews are below 50%.')
    if safety_events >= 3:
        guidance.append('Safety pressure elevated: repeated safety events observed in this run.')
    if pnl >= Decimal('0') and favorable_rate >= Decimal('0.60') and safety_events == 0:
        guidance.append('Paper performance appears stable under current constraints.')

    if not guidance:
        guidance.append('No strong risk signal detected. Continue monitoring with more sessions for confidence.')
    return guidance
