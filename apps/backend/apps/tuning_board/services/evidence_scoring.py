from decimal import Decimal

from apps.evaluation_lab.models import EffectivenessMetricStatus
from apps.tuning_board.models import TuningPriorityLevel, TuningProposalStatus


def score_evidence(candidate: dict) -> dict:
    metric = candidate.get('source_metric')
    score = Decimal('0.20')
    blockers: list[str] = []

    if metric is not None:
        sample_count = getattr(metric, 'sample_count', 0) or 0
        if sample_count >= 100:
            score += Decimal('0.35')
        elif sample_count >= 40:
            score += Decimal('0.20')
        else:
            score -= Decimal('0.10')
            blockers.append('insufficient_sample_count')

        if metric.status == EffectivenessMetricStatus.POOR:
            score += Decimal('0.30')
        elif metric.status == EffectivenessMetricStatus.CAUTION:
            score += Decimal('0.10')
        else:
            score -= Decimal('0.05')

    reason_codes = set(candidate.get('reason_codes') or [])
    if 'LOW_SAMPLE' in reason_codes:
        score -= Decimal('0.20')
        blockers.append('requires_more_data')

    score = max(Decimal('0.0'), min(Decimal('1.0'), score))

    if blockers:
        status = TuningProposalStatus.WATCH
    elif score >= Decimal('0.75'):
        status = TuningProposalStatus.READY_FOR_REVIEW
    elif score >= Decimal('0.45'):
        status = TuningProposalStatus.PROPOSED
    else:
        status = TuningProposalStatus.DEFERRED

    if score >= Decimal('0.85'):
        priority = TuningPriorityLevel.CRITICAL
    elif score >= Decimal('0.65'):
        priority = TuningPriorityLevel.HIGH
    elif score >= Decimal('0.45'):
        priority = TuningPriorityLevel.MEDIUM
    else:
        priority = TuningPriorityLevel.LOW

    return {
        **candidate,
        'evidence_strength_score': score,
        'proposal_status': candidate.get('proposal_status') or status,
        'priority_level': priority,
        'blockers': sorted(set(candidate.get('blockers') or []).union(blockers)),
    }
