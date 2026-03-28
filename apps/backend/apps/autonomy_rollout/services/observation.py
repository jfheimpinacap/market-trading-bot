from __future__ import annotations

from django.utils import timezone

from apps.autonomy_rollout.models import AutonomyPostChangeSnapshot, AutonomyRolloutRun
from apps.autonomy_rollout.services.baseline import collect_snapshot_payload
from apps.autonomy_rollout.services.comparison import build_metric_deltas


def capture_post_change_snapshot(run: AutonomyRolloutRun) -> AutonomyPostChangeSnapshot:
    since = run.autonomy_stage_transition.applied_at
    payload = collect_snapshot_payload(action_types=list(run.domain.action_types or []), source_apps=list(run.domain.source_apps or []), since=since)
    deltas = build_metric_deltas(baseline_metrics=run.baseline_snapshot.metrics, post_metrics=payload.metrics)
    sample_size = int(payload.metrics.get('sample_size') or 0)
    confidence = min(sample_size / 20, 1)

    snapshot, _created = AutonomyPostChangeSnapshot.objects.update_or_create(
        run=run,
        defaults={
            'metrics': payload.metrics,
            'counts': payload.counts,
            'deltas': deltas,
            'sample_size': sample_size,
            'confidence': f'{confidence:.4f}',
        },
    )
    run.metadata = {
        **(run.metadata or {}),
        'last_observed_at': timezone.now().isoformat(),
        'observation_age_days': max((timezone.now() - run.autonomy_stage_transition.applied_at).days, 0),
    }
    run.save(update_fields=['metadata', 'updated_at'])
    return snapshot
