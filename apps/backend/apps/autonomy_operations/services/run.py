from __future__ import annotations

from collections import Counter

from django.db import transaction

from apps.autonomy_operations.models import CampaignRuntimeSnapshot, OperationsRun
from apps.autonomy_operations.services.attention import generate_attention_signals
from apps.autonomy_operations.services.progress import compute_progress
from apps.autonomy_operations.services.recommendation import build_recommendations
from apps.autonomy_operations.services.runtime import build_runtime_context, list_active_campaigns


@transaction.atomic
def run_monitor_cycle(*, actor: str = 'operator-ui'):
    contexts = [build_runtime_context(campaign) for campaign in list_active_campaigns()]
    snapshots = []

    for context in contexts:
        progress = compute_progress(context)
        snapshot = CampaignRuntimeSnapshot.objects.create(
            campaign=context.campaign,
            campaign_status=context.campaign.status,
            current_wave=context.campaign.current_wave,
            current_step=context.current_step,
            current_checkpoint=context.current_checkpoint,
            started_at=context.started_at,
            last_progress_at=progress['last_progress_at'],
            stalled_duration_seconds=progress['stalled_duration_seconds'],
            open_checkpoints_count=context.open_checkpoints_count,
            pending_approvals_count=context.pending_approvals_count,
            blocked_steps_count=context.blocked_steps_count,
            incident_impact=context.incident_impact,
            degraded_impact=context.degraded_impact,
            rollout_observation_impact=context.rollout_observation_impact,
            progress_score=progress['progress_score'],
            runtime_status=progress['runtime_status'],
            blockers=context.blockers,
            metadata={**context.metadata, 'actor': actor},
        )
        snapshots.append(snapshot)

    signals = []
    for snapshot in snapshots:
        signals.extend(generate_attention_signals(snapshot))

    status_counter = Counter(snapshot.runtime_status for snapshot in snapshots)
    operations_run = OperationsRun.objects.create(
        active_campaign_count=len(snapshots),
        on_track_count=status_counter.get('ON_TRACK', 0),
        caution_count=status_counter.get('CAUTION', 0),
        stalled_count=status_counter.get('STALLED', 0),
        blocked_count=status_counter.get('BLOCKED', 0),
        waiting_approval_count=status_counter.get('WAITING_APPROVAL', 0),
        observing_count=status_counter.get('OBSERVING', 0),
        attention_signal_count=len(signals),
        recommendation_summary={},
        metadata={'actor': actor},
    )

    recommendations = build_recommendations(operations_run=operations_run, snapshots=snapshots, signals=signals)
    recommendation_counter = Counter(item.recommendation_type for item in recommendations)
    operations_run.recommendation_summary = dict(recommendation_counter)
    operations_run.save(update_fields=['recommendation_summary', 'updated_at'])

    return {
        'run': operations_run,
        'snapshots': snapshots,
        'signals': signals,
        'recommendations': recommendations,
    }
