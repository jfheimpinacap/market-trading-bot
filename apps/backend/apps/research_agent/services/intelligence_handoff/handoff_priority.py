from __future__ import annotations

from decimal import Decimal

from apps.research_agent.models import (
    NarrativeConsensusState,
    NarrativeDivergenceState,
    ResearchHandoffPriority,
    ResearchHandoffStatus,
    ResearchPriorityBucket,
)


def build_handoff_priorities(*, run, consensus_records, divergence_by_consensus_id):
    priorities = []
    for consensus in consensus_records:
        divergence = divergence_by_consensus_id.get(consensus.id)
        score = Decimal('0.0000')
        reason_codes = []

        if consensus.consensus_state == NarrativeConsensusState.STRONG_CONSENSUS:
            score += Decimal('0.45')
            reason_codes.append('strong_consensus')
        elif consensus.consensus_state == NarrativeConsensusState.WEAK_CONSENSUS:
            score += Decimal('0.25')
            reason_codes.append('weak_consensus')
        elif consensus.consensus_state == NarrativeConsensusState.CONFLICTED:
            score -= Decimal('0.35')
            reason_codes.append('conflicted_narrative')

        score += (consensus.intensity_score * Decimal('0.20'))
        score += (consensus.novelty_score * Decimal('0.15'))
        score += (consensus.persistence_score * Decimal('0.10'))

        if divergence:
            if divergence.divergence_state == NarrativeDivergenceState.HIGH_DIVERGENCE:
                score += Decimal('0.35')
                reason_codes.append('high_market_divergence')
            elif divergence.divergence_state == NarrativeDivergenceState.MODEST_DIVERGENCE:
                score += Decimal('0.15')
                reason_codes.append('modest_market_divergence')
            elif divergence.divergence_state == NarrativeDivergenceState.ALIGNED:
                reason_codes.append('market_aligned')

        score = max(Decimal('0.0000'), min(Decimal('1.0000'), score)).quantize(Decimal('0.0001'))

        if consensus.consensus_state == NarrativeConsensusState.CONFLICTED:
            bucket = ResearchPriorityBucket.IGNORE
            status = ResearchHandoffStatus.BLOCKED
        elif score >= Decimal('0.80'):
            bucket = ResearchPriorityBucket.CRITICAL
            status = ResearchHandoffStatus.READY_FOR_RESEARCH
        elif score >= Decimal('0.62'):
            bucket = ResearchPriorityBucket.HIGH
            status = ResearchHandoffStatus.READY_FOR_RESEARCH
        elif score >= Decimal('0.45'):
            bucket = ResearchPriorityBucket.MEDIUM
            status = ResearchHandoffStatus.WATCHLIST
        elif score >= Decimal('0.28'):
            bucket = ResearchPriorityBucket.LOW
            status = ResearchHandoffStatus.DEFERRED
        else:
            bucket = ResearchPriorityBucket.IGNORE
            status = ResearchHandoffStatus.DEFERRED

        priority = ResearchHandoffPriority.objects.create(
            consensus_run=run,
            linked_consensus_record=consensus,
            linked_divergence_record=divergence,
            linked_market=divergence.linked_market if divergence else None,
            priority_bucket=bucket,
            handoff_status=status,
            priority_reason_codes=reason_codes,
            priority_score=score,
            handoff_summary=f"{bucket} priority ({status}) from consensus={consensus.consensus_state} and divergence={divergence.divergence_state if divergence else 'none'}.",
            metadata={},
        )
        priorities.append(priority)
    return priorities
