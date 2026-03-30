from __future__ import annotations

from decimal import Decimal

from apps.research_agent.models import NarrativeSignal


def link_narrative_signals(*, market):
    signals = list(
        NarrativeSignal.objects.filter(linked_market=market)
        .order_by('-total_signal_score', '-created_at_scan')[:8]
    )
    if not signals:
        return {
            'linked_signals': [],
            'narrative_support_score': Decimal('0.0000'),
            'divergence_score': Decimal('0.0000'),
            'reason_codes': ['no_scan_signals'],
        }

    support = sum(Decimal(str(signal.total_signal_score or '0')) for signal in signals) / Decimal(len(signals))
    divergence = max(Decimal(str(signal.market_divergence_score or '0')) for signal in signals)
    return {
        'linked_signals': [
            {
                'id': signal.id,
                'label': signal.canonical_label,
                'status': signal.status,
                'total_signal_score': str(signal.total_signal_score),
            }
            for signal in signals
        ],
        'narrative_support_score': min(Decimal('1.0000'), support).quantize(Decimal('0.0001')),
        'divergence_score': min(Decimal('1.0000'), divergence).quantize(Decimal('0.0001')),
        'reason_codes': [],
    }
