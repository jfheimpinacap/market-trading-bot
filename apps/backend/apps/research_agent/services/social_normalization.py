from __future__ import annotations

from decimal import Decimal


def clamp01(value: float | int | Decimal, default: float = 0.0) -> Decimal:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = default
    numeric = max(0.0, min(numeric, 1.0))
    return Decimal(f'{numeric:.4f}')


def normalize_social_metrics(metadata: dict) -> tuple[Decimal, Decimal, Decimal]:
    social_signal = clamp01(metadata.get('social_signal_strength', 0.3), default=0.3)
    hype_risk = clamp01(metadata.get('hype_risk', 0.25), default=0.25)
    noise_risk = clamp01(metadata.get('noise_risk', 0.25), default=0.25)
    return social_signal, hype_risk, noise_risk


def compute_cross_source_agreement(source_pressures: dict[str, Decimal]) -> tuple[Decimal, Decimal]:
    non_zero = [value for value in source_pressures.values() if value != Decimal('0.0000')]
    if len(non_zero) < 2:
        return Decimal('0.5000'), Decimal('0.5000')
    sign = lambda v: 1 if v > 0 else -1
    same = 0
    total = 0
    for idx, first in enumerate(non_zero):
        for second in non_zero[idx + 1 :]:
            total += 1
            if sign(first) == sign(second):
                same += 1
    agreement = Decimal(same) / Decimal(max(total, 1))
    return agreement.quantize(Decimal('0.0001')), (Decimal('1.0000') - agreement).quantize(Decimal('0.0001'))
