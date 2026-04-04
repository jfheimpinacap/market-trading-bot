from __future__ import annotations

from collections import Counter

from django.utils import timezone

from apps.runtime_governor.models import GlobalModeEnforcementRun
from apps.runtime_governor.mode_enforcement.services.enforcement import apply_module_enforcement, build_downstream_enforcement_summary
from apps.runtime_governor.mode_enforcement.services.module_impacts import build_module_impacts
from apps.runtime_governor.mode_enforcement.services.recommendation import emit_enforcement_recommendations
from apps.runtime_governor.mode_enforcement.services.rules import list_rules_for_mode
from apps.runtime_governor.services.operating_mode.mode_switch import get_active_global_operating_mode
from apps.runtime_governor.services.state import get_runtime_state
from apps.runtime_governor.services.tuning_context import build_runtime_tuning_context


def run_mode_enforcement_review(*, triggered_by: str = 'operator-ui') -> dict:
    current_mode = get_active_global_operating_mode()
    run = GlobalModeEnforcementRun.objects.create(current_mode=current_mode, metadata={'triggered_by': triggered_by})
    rules = list_rules_for_mode(current_mode)
    impacts = build_module_impacts(enforcement_run=run, current_mode=current_mode, rules=rules)
    decisions = apply_module_enforcement(enforcement_run=run, impacts=impacts)
    recommendations = emit_enforcement_recommendations(enforcement_run=run, impacts=impacts, decisions=decisions)

    counts = Counter(i.impact_status for i in impacts)
    run.considered_module_count = len(rules)
    run.affected_module_count = len([i for i in impacts if i.impact_status != 'UNCHANGED'])
    run.restricted_module_count = len([i for i in impacts if i.impact_status in {'REDUCED', 'THROTTLED', 'MONITOR_ONLY', 'BLOCKED'}])
    run.throttled_module_count = counts.get('THROTTLED', 0)
    run.blocked_module_count = counts.get('BLOCKED', 0)
    run.monitor_only_module_count = counts.get('MONITOR_ONLY', 0)
    run.recommendation_summary = {'count': len(recommendations), 'latest_type': recommendations[0].recommendation_type if recommendations else None}
    run.metadata = {
        **(run.metadata or {}),
        'decision_count': len(decisions),
        'impact_count': len(impacts),
    }
    run.completed_at = timezone.now()
    run.save()

    state = get_runtime_state()
    metadata = dict(state.metadata or {})
    metadata['global_mode_enforcement'] = build_downstream_enforcement_summary(current_mode=current_mode, decisions=decisions, impacts=impacts)
    metadata['global_mode_enforcement_run_id'] = run.id
    state.metadata = metadata
    state.save(update_fields=['metadata', 'updated_at'])

    return {
        'run': run,
        'impacts': impacts,
        'decisions': decisions,
        'recommendations': recommendations,
    }


def get_mode_enforcement_summary() -> dict:
    latest = GlobalModeEnforcementRun.objects.order_by('-started_at', '-id').first()
    if not latest:
        summary = {
            'latest_run_id': None,
            'current_mode': get_active_global_operating_mode(),
            'modules_affected': 0,
            'reduced_count': 0,
            'throttled_count': 0,
            'monitor_only_count': 0,
            'blocked_count': 0,
            'recommendation_summary': {},
        }
        summary.update(build_runtime_tuning_context(summary_scope='mode_enforcement_summary'))
        return summary
    summary = {
        'latest_run_id': latest.id,
        'current_mode': latest.current_mode,
        'modules_affected': latest.affected_module_count,
        'reduced_count': latest.restricted_module_count - latest.throttled_module_count - latest.monitor_only_module_count - latest.blocked_module_count,
        'throttled_count': latest.throttled_module_count,
        'monitor_only_count': latest.monitor_only_module_count,
        'blocked_count': latest.blocked_module_count,
        'recommendation_summary': latest.recommendation_summary,
    }
    summary.update(build_runtime_tuning_context(summary_scope='mode_enforcement_summary'))
    return summary
