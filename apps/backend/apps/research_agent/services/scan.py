from __future__ import annotations

from django.utils import timezone

from apps.research_agent.models import ResearchScanRun, ResearchScanRunStatus
from apps.research_agent.services.analyze import run_narrative_analysis
from apps.research_agent.services.ingest import run_rss_ingest
from apps.research_agent.services.linking import link_narratives_to_markets
from apps.research_agent.services.shortlist import generate_research_candidates


def run_research_scan(*, source_ids: list[int] | None = None, run_analysis: bool = True) -> ResearchScanRun:
    started = timezone.now()
    ingest_result = run_rss_ingest(source_ids=source_ids)
    analyzed_count = 0
    link_count = 0
    candidate_count = 0
    errors = list(ingest_result.errors)

    if run_analysis:
        analysis_result = run_narrative_analysis()
        analyzed_count = analysis_result.analyzed
        errors.extend(analysis_result.errors)

    link_count = link_narratives_to_markets()
    candidate_count = generate_research_candidates()

    status = ResearchScanRunStatus.SUCCESS
    if errors:
        status = ResearchScanRunStatus.PARTIAL if ingest_result.items_created or analyzed_count else ResearchScanRunStatus.FAILED

    return ResearchScanRun.objects.create(
        status=status,
        triggered_by='manual',
        sources_scanned=ingest_result.sources_scanned,
        items_created=ingest_result.items_created,
        items_deduplicated=ingest_result.items_deduplicated,
        analyses_generated=analyzed_count,
        candidates_generated=candidate_count,
        started_at=started,
        finished_at=timezone.now(),
        errors=errors,
        metadata={'links_generated': link_count, 'run_analysis': run_analysis},
    )
