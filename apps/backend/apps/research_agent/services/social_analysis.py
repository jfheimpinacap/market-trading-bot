from __future__ import annotations

from apps.research_agent.models import NarrativeItem, NarrativeSourceType
from apps.research_agent.services.analyze import AnalysisResult, run_narrative_analysis


def run_social_narrative_analysis(*, item_ids: list[int] | None = None) -> AnalysisResult:
    queryset = NarrativeItem.objects.filter(source__source_type=NarrativeSourceType.REDDIT)
    if item_ids:
        queryset = queryset.filter(id__in=item_ids)
    target_ids = list(queryset.values_list('id', flat=True)[:150])
    return run_narrative_analysis(item_ids=target_ids)
