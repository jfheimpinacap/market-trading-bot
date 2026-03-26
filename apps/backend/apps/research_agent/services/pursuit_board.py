from __future__ import annotations

from django.db.models import Count

from apps.research_agent.models import MarketUniverseScanRun, PursuitCandidate, TriageStatus


def get_latest_board_summary() -> dict:
    latest_run = MarketUniverseScanRun.objects.order_by('-started_at', '-id').first()
    if not latest_run:
        return {
            'latest_scan': None,
            'markets_considered': 0,
            'markets_filtered_out': 0,
            'markets_shortlisted': 0,
            'markets_watchlist': 0,
            'top_exclusion_reasons': [],
            'status_breakdown': {
                TriageStatus.SHORTLISTED: 0,
                TriageStatus.WATCH: 0,
                TriageStatus.FILTERED_OUT: 0,
            },
        }

    decisions = latest_run.triage_decisions.values('triage_status').annotate(total=Count('id'))
    status_breakdown = {
        TriageStatus.SHORTLISTED: 0,
        TriageStatus.WATCH: 0,
        TriageStatus.FILTERED_OUT: 0,
    }
    for item in decisions:
        status_breakdown[item['triage_status']] = item['total']

    return {
        'latest_scan': {
            'id': latest_run.id,
            'status': latest_run.status,
            'filter_profile': latest_run.filter_profile,
            'started_at': latest_run.started_at,
            'finished_at': latest_run.finished_at,
            'summary': latest_run.summary,
        },
        'markets_considered': latest_run.markets_considered,
        'markets_filtered_out': latest_run.markets_filtered_out,
        'markets_shortlisted': latest_run.markets_shortlisted,
        'markets_watchlist': latest_run.markets_watchlist,
        'top_exclusion_reasons': latest_run.details.get('top_exclusion_reasons', []) if latest_run.details else [],
        'status_breakdown': status_breakdown,
    }


def get_pursuit_candidates_queryset(*, status: str | None = None):
    queryset = PursuitCandidate.objects.select_related('market', 'market__provider', 'run').order_by('-triage_score', '-created_at')
    if status:
        queryset = queryset.filter(triage_status=status)
    return queryset[:200]
