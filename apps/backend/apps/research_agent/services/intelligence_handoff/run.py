from __future__ import annotations

from collections import Counter

from django.utils import timezone

from apps.research_agent.models import (
    NarrativeConsensusRecord,
    NarrativeConsensusRun,
    NarrativeConsensusState,
    NarrativeDivergenceState,
    NarrativeMarketDivergenceRecord,
    NarrativeSignal,
    ResearchHandoffPriority,
    ResearchHandoffStatus,
)
from apps.research_agent.services.intelligence_handoff.consensus import build_consensus_records
from apps.research_agent.services.intelligence_handoff.divergence import build_divergence_records
from apps.research_agent.services.intelligence_handoff.handoff_priority import build_handoff_priorities
from apps.research_agent.services.intelligence_handoff.recommendation import build_consensus_recommendations


def run_consensus_review(*, triggered_by: str = 'manual_api') -> NarrativeConsensusRun:
    run = NarrativeConsensusRun.objects.create(started_at=timezone.now(), metadata={'triggered_by': triggered_by})
    signals = list(NarrativeSignal.objects.select_related('linked_cluster', 'linked_market').order_by('-created_at_scan', '-id')[:400])

    consensus_records = build_consensus_records(run=run, signals=signals)
    divergences = build_divergence_records(run=run, consensus_records=consensus_records)
    divergence_by_consensus_id = {item.linked_consensus_record_id: item for item in divergences}
    priorities = build_handoff_priorities(run=run, consensus_records=consensus_records, divergence_by_consensus_id=divergence_by_consensus_id)
    recommendations = build_consensus_recommendations(run=run, handoff_priorities=priorities)

    recommendation_summary = Counter(item.recommendation_type for item in recommendations)
    run.completed_at = timezone.now()
    run.considered_signal_count = len(signals)
    run.considered_cluster_count = len([item for item in consensus_records if item.linked_cluster_id])
    run.consensus_detected_count = len([item for item in consensus_records if item.consensus_state in {NarrativeConsensusState.STRONG_CONSENSUS, NarrativeConsensusState.WEAK_CONSENSUS}])
    run.conflict_detected_count = len([item for item in consensus_records if item.consensus_state == NarrativeConsensusState.CONFLICTED])
    run.divergence_detected_count = len([item for item in divergences if item.divergence_state == NarrativeDivergenceState.HIGH_DIVERGENCE])
    run.priority_handoff_count = len([item for item in priorities if item.handoff_status == ResearchHandoffStatus.READY_FOR_RESEARCH])
    run.recommendation_summary = dict(recommendation_summary)
    run.metadata = {**(run.metadata or {}), 'record_count': len(consensus_records)}
    run.save()
    return run


def get_consensus_summary():
    latest = NarrativeConsensusRun.objects.order_by('-started_at', '-id').first()
    if not latest:
        return {
            'latest_run': None,
            'signals_considered': 0,
            'clusters_considered': 0,
            'strong_consensus_count': 0,
            'conflicted_count': 0,
            'high_divergence_count': 0,
            'ready_for_research_count': 0,
            'recommendation_summary': {},
        }

    return {
        'latest_run': latest.id,
        'signals_considered': latest.considered_signal_count,
        'clusters_considered': latest.considered_cluster_count,
        'strong_consensus_count': NarrativeConsensusRecord.objects.filter(consensus_run=latest, consensus_state=NarrativeConsensusState.STRONG_CONSENSUS).count(),
        'conflicted_count': NarrativeConsensusRecord.objects.filter(consensus_run=latest, consensus_state=NarrativeConsensusState.CONFLICTED).count(),
        'high_divergence_count': NarrativeMarketDivergenceRecord.objects.filter(consensus_run=latest, divergence_state=NarrativeDivergenceState.HIGH_DIVERGENCE).count(),
        'ready_for_research_count': ResearchHandoffPriority.objects.filter(consensus_run=latest, handoff_status=ResearchHandoffStatus.READY_FOR_RESEARCH).count(),
        'recommendation_summary': latest.recommendation_summary,
    }
