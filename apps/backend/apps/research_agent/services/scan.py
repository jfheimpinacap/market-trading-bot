from __future__ import annotations

from django.utils import timezone

from apps.research_agent.models import ResearchScanRun, ResearchScanRunStatus
from apps.research_agent.services.analyze import run_narrative_analysis
from apps.research_agent.services.ingest import merge_ingest_results, run_rss_ingest
from apps.research_agent.services.linking import link_narratives_to_markets
from apps.research_agent.services.reddit_ingest import run_reddit_ingest
from apps.research_agent.services.shortlist import generate_research_candidates


def run_research_scan(*, source_ids: list[int] | None = None, run_analysis: bool = True) -> ResearchScanRun:
    started = timezone.now()
    ingest_result = merge_ingest_results(run_rss_ingest(source_ids=source_ids), run_reddit_ingest(source_ids=source_ids))
    analyzed_count = 0
    degraded_count = 0
    link_count = 0
    candidate_count = 0
    errors = list(ingest_result.errors)

    if run_analysis:
        analysis_result = run_narrative_analysis()
        analyzed_count = analysis_result.analyzed
        degraded_count = analysis_result.degraded
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
        rss_items_created=ingest_result.rss_items_created,
        reddit_items_created=ingest_result.reddit_items_created,
        items_deduplicated=ingest_result.items_deduplicated,
        analyses_generated=analyzed_count,
        analyses_degraded=degraded_count,
        candidates_generated=candidate_count,
        started_at=started,
        finished_at=timezone.now(),
        errors=errors,
        source_errors=ingest_result.source_errors or {},
        metadata={'links_generated': link_count, 'run_analysis': run_analysis},
    )


def run_full_research_scan(*, source_ids: list[int] | None = None) -> ResearchScanRun:
    return run_research_scan(source_ids=source_ids, run_analysis=True)
