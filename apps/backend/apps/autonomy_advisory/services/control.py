from __future__ import annotations

from apps.autonomy_advisory.models import AdvisoryArtifact, AdvisoryArtifactStatus
from apps.autonomy_insights.models import CampaignInsight
from .emission import emit_advisory_artifact


def emit_advisory_for_insight(*, insight_id: int, actor: str = 'operator-ui', advisory_run=None) -> AdvisoryArtifact:
    insight = CampaignInsight.objects.select_related('campaign').get(id=insight_id)
    if not insight.reviewed:
        return AdvisoryArtifact.objects.create(
            advisory_run=advisory_run,
            insight=insight,
            campaign=insight.campaign,
            artifact_type='MANAGER_REVIEW_NOTE',
            artifact_status=AdvisoryArtifactStatus.BLOCKED,
            target_scope='operator_review',
            summary=f'Insight #{insight.id} blocked for advisory emission',
            rationale='Insight must be reviewed before advisory emission.',
            reason_codes=['insight_not_reviewed'],
            blockers=['INSIGHT_NOT_REVIEWED'],
            metadata={'insight_reviewed': insight.reviewed},
        )

    return emit_advisory_artifact(insight=insight, actor=actor, advisory_run=advisory_run)
