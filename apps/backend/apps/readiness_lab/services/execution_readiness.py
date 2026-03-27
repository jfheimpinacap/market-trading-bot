from __future__ import annotations

from apps.replay_lab.models import ReplayRun


def summarize_execution_realism() -> dict:
    aware_runs = ReplayRun.objects.filter(details__execution_mode='execution_aware').order_by('-created_at', '-id')[:20]
    total = aware_runs.count()
    if total == 0:
        return {
            'execution_aware_runs': 0,
            'avg_fill_rate': 0.0,
            'avg_no_fill_rate': 0.0,
            'avg_execution_drag': 0.0,
            'avg_execution_realism_score': 0.0,
            'readiness_penalty': 0.25,
            'summary': 'No execution-aware replay evidence. Run replay with execution-aware mode to measure fill realism.',
        }

    fill_rate_values = []
    no_fill_values = []
    drag_values = []
    realism_values = []

    for run in aware_runs:
        impact = (run.details or {}).get('execution_impact_summary', {})
        fill_rate_values.append(float(impact.get('fill_rate', 0)))
        no_fill_values.append(float(impact.get('no_fill_rate', 0)))
        drag_values.append(float(impact.get('execution_drag', 0)))
        realism_values.append(float(impact.get('execution_realism_score', 0)))

    avg_fill_rate = sum(fill_rate_values) / total
    avg_no_fill_rate = sum(no_fill_values) / total
    avg_drag = sum(drag_values) / total
    avg_realism_score = sum(realism_values) / total
    readiness_penalty = max(0.0, min(0.35, (avg_no_fill_rate * 0.20) + ((1 - avg_realism_score) * 0.15)))

    return {
        'execution_aware_runs': total,
        'avg_fill_rate': round(avg_fill_rate, 4),
        'avg_no_fill_rate': round(avg_no_fill_rate, 4),
        'avg_execution_drag': round(avg_drag, 2),
        'avg_execution_realism_score': round(avg_realism_score, 4),
        'readiness_penalty': round(readiness_penalty, 4),
        'summary': 'Execution-aware evidence integrated into readiness scoring.',
    }
