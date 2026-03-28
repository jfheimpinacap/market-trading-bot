from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.policy_rollout.models import PolicyPostChangeSnapshot, PolicyRolloutRun
from apps.policy_rollout.services.baseline import collect_snapshot_payload
from apps.policy_rollout.services.comparison import build_metric_deltas


def capture_post_change_snapshot(run: PolicyRolloutRun) -> PolicyPostChangeSnapshot:
    since = run.application_log.applied_at
    payload = collect_snapshot_payload(action_type=run.policy_tuning_candidate.action_type, since=since)
    deltas = build_metric_deltas(baseline_metrics=run.baseline_snapshot.metrics, post_metrics=payload.metrics)
    sample_size = int(payload.metrics.get('sample_size') or 0)
    confidence = min(sample_size / 20, 1)

    snapshot, _created = PolicyPostChangeSnapshot.objects.update_or_create(
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
        'observation_age_days': max((timezone.now() - run.application_log.applied_at).days, 0),
    }
    run.save(update_fields=['metadata', 'updated_at'])
    return snapshot
