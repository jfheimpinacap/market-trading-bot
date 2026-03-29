from __future__ import annotations

from collections import Counter

from django.db import transaction

from apps.autonomy_recovery.models import RecoveryRecommendation, RecoveryRun, RecoverySnapshot
from apps.autonomy_recovery.services.candidates import build_recovery_candidates
from apps.autonomy_recovery.services.readiness import evaluate_recovery_readiness
from apps.autonomy_recovery.services.recommendation import create_recommendation


@transaction.atomic
def run_recovery_review(*, actor: str = 'operator-ui'):
    candidate_contexts = build_recovery_candidates()
    snapshots: list[RecoverySnapshot] = []

    for context in candidate_contexts:
        readiness = evaluate_recovery_readiness(context)
        snapshot = RecoverySnapshot.objects.create(
            campaign=context.campaign,
            base_campaign_status=context.campaign.status,
            last_progress_at=context.runtime.last_progress_at if context.runtime else None,
            paused_duration_seconds=readiness['paused_duration_seconds'],
            blocker_count=readiness['blocker_count'],
            blocker_types=readiness['blocker_types'],
            approvals_pending=context.pending_approvals_count > 0,
            checkpoints_pending=context.pending_checkpoints_count > 0,
            incident_pressure_level=readiness['incident_pressure_level'],
            recovery_score=readiness['recovery_score'],
            recovery_priority=readiness['recovery_priority'],
            resume_readiness=readiness['resume_readiness'],
            recovery_status=readiness['recovery_status'],
            rationale=readiness['rationale'],
            metadata={
                'blockers': readiness['blockers'],
                'pending_approvals_count': context.pending_approvals_count,
                'pending_checkpoints_count': context.pending_checkpoints_count,
                'last_intervention_request': context.last_request.id if context.last_request else None,
                'last_intervention_action': context.last_action.id if context.last_action else None,
                'last_intervention_outcome': context.last_outcome.id if context.last_outcome else None,
                'actor': actor,
            },
        )
        snapshots.append(snapshot)

    status_counter = Counter(snapshot.recovery_status for snapshot in snapshots)
    run = RecoveryRun.objects.create(
        candidate_count=len(snapshots),
        ready_to_resume_count=status_counter.get('READY_TO_RESUME', 0),
        keep_paused_count=status_counter.get('KEEP_PAUSED', 0),
        blocked_count=status_counter.get('BLOCKED', 0),
        review_abort_count=status_counter.get('REVIEW_ABORT', 0),
        close_candidate_count=status_counter.get('CLOSE_CANDIDATE', 0),
        approval_required_count=sum(1 for snapshot in snapshots if snapshot.approvals_pending),
        recommendation_summary={},
        metadata={'actor': actor},
    )

    recommendations = [create_recommendation(run=run, context=context, snapshot=snapshot, actor=actor) for context, snapshot in zip(candidate_contexts, snapshots)]

    ready_snapshots = sorted((s for s in snapshots if s.recovery_status == 'READY_TO_RESUME'), key=lambda item: item.recovery_priority)
    if len(ready_snapshots) > 1:
        recommendations.append(
            RecoveryRecommendation.objects.create(
                recovery_run=run,
                recommendation_type='REORDER_RECOVERY_PRIORITY',
                target_campaign=None,
                rationale='Multiple campaigns are recoverable; apply priority order before manual resume actions.',
                reason_codes=['multiple_ready_campaigns', 'prioritize_recovery_order'],
                confidence=0.82,
                blockers=[],
                impacted_domains=[],
                metadata={'actor': actor, 'priority_campaign_ids': [s.campaign_id for s in ready_snapshots]},
            )
        )

    recommendation_counter = Counter(item.recommendation_type for item in recommendations)
    run.recommendation_summary = dict(recommendation_counter)
    run.save(update_fields=['recommendation_summary', 'updated_at'])

    return {'run': run, 'snapshots': snapshots, 'recommendations': recommendations}
